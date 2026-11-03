from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path so 'core' module can be imported regardless of execution location
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os, json, asyncio, re
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from core.schema import DATA, load_all
from models.chat_model import llm

CARDS = DATA / "cards.jsonl"


class ConceptCard(BaseModel):
    core_technique: str = Field(description="Primary algorithm/paradigm, e.g. 'rerooting tree DP', 'monotonic stack', 'binary search on answer'")
    secondary_techniques: list[str] = Field(default_factory=list, max_length=4)
    reduction: str = Field(description="The abstract task once the story is removed. 2-3 sentences. Say what is being computed over what structure, never using the story's nouns.")
    data_structures: list[str] = Field(default_factory=list, max_length=5)
    key_insight: str = Field(description="The observation that unlocks the problem — the thing an editorial would lead with.")
    complexity: str = Field(description="Intended complexity, e.g. 'O(n log n)'")
    constraint_regime: str = Field(description="What the limits force, e.g. 'n<=2e5 rules out O(n^2)', 'n<=20 permits bitmask DP'")
    canonical_tags: list[str] = Field(description="3-6 normalized tags from a fixed vocabulary", max_length=6)
    pitfalls: list[str] = Field(default_factory=list, max_length=3)


VOCABULARY = """two-pointers, sliding-window, prefix-sums, binary-search, binary-search-on-answer,
ternary-search, sorting, greedy, exchange-argument, dp-linear, dp-knapsack, dp-interval,
dp-bitmask, dp-digit, dp-tree, dp-rerooting, dp-on-broken-profile, dp-optimization-cht,
divide-and-conquer, dnc-optimization, graph-bfs, graph-dfs, shortest-paths, mst,
topological-sort, scc, bridges-articulation, bipartite-matching, max-flow, min-cut,
union-find, segment-tree, segment-tree-lazy, fenwick, sparse-table, lca, hld,
small-to-large, mo-algorithm, trie, string-hashing, kmp, z-function, suffix-automaton,
aho-corasick, manacher, number-theory, modular-arithmetic, combinatorics, inclusion-exclusion,
probability, expected-value, matrix-exponentiation, ntt-fft, game-theory, sprague-grundy,
geometry, convex-hull, bitmask-enumeration, meet-in-the-middle, sqrt-decomposition,
randomization, constructive, interactive, simulation, implementation"""

VOCAB = VOCABULARY


PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a competitive programming editorial writer. You are given a problem "
     "statement. Produce a platform-neutral algorithmic description of it.\n\n"
     "Hard rules:\n"
     "1. STRIP ALL NARRATIVE. Never mention character names, objects, or story framing "
     "(no 'Appleman', no 'treasure', no 'sandwiches'). Describe the abstract structure: "
     "'a rooted tree with colored vertices', 'an array of integers with point updates'.\n"
     "2. Describe HOW it is solved, not what it is about. Two problems with identical "
     "stories but different techniques must produce different cards; two problems with "
     "unrelated stories and the same technique must produce near-identical cards.\n"
     "3. Choose canonical_tags ONLY from this vocabulary:\n{vocab}\n"
     "4. If you are unsure of the intended solution, describe the most standard approach "
     "consistent with the constraints. Do not hedge in prose."),
    ("human", "Title: {title}\nPlatform difficulty (0-100): {difficulty}\n"
              "Platform tags: {tags}\n\nStatement:\n{statement}"),
])


def build_chain(temperature: float = 0.1):
    distill_llm = llm.bind(temperature=temperature) if hasattr(llm, "bind") else llm
    return PROMPT | distill_llm.with_structured_output(ConceptCard)


def card_to_text(title: str, platform: str, c: dict) -> str:
    """The string that actually gets embedded. Order matters — technique first."""
    return (
        f"Technique: {c['core_technique']}. "
        f"Also: {', '.join(c.get('secondary_techniques') or []) or 'none'}.\n"
        f"Tags: {', '.join(c.get('canonical_tags') or [])}.\n"
        f"Task: {c['reduction']}\n"
        f"Key insight: {c['key_insight']}\n"
        f"Structures: {', '.join(c.get('data_structures') or []) or 'none'}.\n"
        f"Complexity: {c['complexity']}. Regime: {c['constraint_regime']}\n"
        f"Title: {title} ({platform})"
    )


async def _process(chain, sem, p: dict):
    async with sem:
        try:
            diff = p.get("difficulty")
            diff_str = str(diff) if diff is not None else "unknown"
            tags_str = ", ".join(p.get("tags") or []) or "none"
            card = await chain.ainvoke({
                "vocab": VOCABULARY,
                "title": p.get("title", ""),
                "difficulty": diff_str,
                "tags": tags_str,
                "statement": (p.get("statement") or "")[:4000],
            })
            card_dict = card.model_dump() if hasattr(card, "model_dump") else card
            return {
                "problem_id": p.get("problem_id", ""),
                "card": card_dict,
            }
        except Exception as e:
            print(f"fail {p.get('problem_id')}: {type(e).__name__}: {e}", flush=True)
            return None


async def process(concurrency: int = 1, limit: int | None = None, platform: str | None = None):
    from core.schema import load_all

    problems = {p["problem_id"]: p for p in load_all()}
    if platform:
        norm = platform.strip().lower()
        alias = {
            "leetcode": "leetcode", "lc": "leetcode",
            "codeforces": "codeforces", "cf": "codeforces",
            "atcoder": "atcoder", "ac": "atcoder",
        }.get(norm, norm)
        problems = {
            pid: p for pid, p in problems.items()
            if p.get("platform", "").lower() == alias or pid.startswith(f"{norm}:")
        }

    done = set()
    if CARDS.exists():
        with CARDS.open(encoding="utf-8") as f:
            done = {json.loads(l)["problem_id"] for l in f if l.strip()}

    todo = [p for pid, p in problems.items() if pid not in done]
    total_todo = len(todo)
    if limit is not None:
        todo = todo[:limit]

    print(f"Cards: {len(problems)} problems loaded, {len(done)} already done, {total_todo} eligible ({len(todo)} to process).", flush=True)
    if not todo:
        print("Nothing to process.", flush=True)
        return

    chain = build_chain(temperature=0.1)
    sem = asyncio.Semaphore(concurrency)

    total = len(todo)
    done_count = 0
    with CARDS.open("a", encoding="utf-8") as out:
        for p in todo:
            pid = p.get("problem_id", "")
            r = await _process(chain, sem, p)
            done_count += 1
            if r:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
                tech = (r.get("card") or {}).get("core_technique", "ok")
                print(f"[{done_count}/{total}] {pid} -> {tech}", flush=True)
            else:
                print(f"[{done_count}/{total}] {pid} (failed)", flush=True)


# Backwards compatibility alias
getConceptCards = process


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract ConceptCards using LLM")
    parser.add_argument("--limit", type=int, default=None, help="Max problems to process")
    parser.add_argument("--concurrency", type=int, default=1, help="Async concurrency (default 1 for local Ollama)")
    parser.add_argument("--platform", type=str, default=None, help="Filter by platform (e.g. leetcode, codeforces, atcoder)")
    args = parser.parse_args()
    asyncio.run(process(concurrency=args.concurrency, limit=args.limit, platform=args.platform))
