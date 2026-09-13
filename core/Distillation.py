from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel,Field
import re,pathlib,asyncio,json
from core.schema import DATA, load_all
from langchain_openai import ChatOpenAI

model=ChatOpenAI(model='openai:gpt-5-mini',temperature=0.2)

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


VOCABULARY ="""two-pointers, sliding-window, prefix-sums, binary-search, binary-search-on-answer,
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


def build_chain():
    model.with_structured_output(ConceptCard)
    return PROMPT | model


def card_to_text(title : str , platform : str,card : dict)-> str:
    return (
        f"Technique: {card['core_technique']}. "
        f"Also: {', '.join(card.get('secondary_techniques') or []) or 'none'}.\n"
        f"Tags: {', '.join(card.get('canonical_tags') or [])}.\n"
        f"Task: {card['reduction']}\n"
        f"Key insight: {card['key_insight']}\n"
        f"Structures: {', '.join(card.get('data_structures') or []) or 'none'}.\n"
        f"Complexity: {card['complexity']}. Regime: {card['constraint_regime']}\n"
        f"Title: {title} ({platform})"
    )
    




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
 
 
 
async def _process(chain, sem, p):
    async with sem:
        try:
            card = await chain.ainvoke({
                "vocab": VOCABULARY,
                "title": p["title"],
                "difficulty": p.get("difficulty"),
                "tags": ", ".join(p.get("tags") or []) or "none",
                "statement": p["statement"][:6000],
            })
            return {"problem_id": p["problem_id"], "card": card.model_dump()}
        except Exception as e:
            print(f"fail {p['problem_id']}: {e}")
            return None
 


async def  getConceptCards(concurrency : int=12) :
    done =set()
    if CARDS.exists :
        with CARDS.open(encoding='utf-8') as f :
            done=[json.loads(l)['problem_id'] for l in f if l.strip()]
            
        todo=[p for p in load_all if p['problem_id'] not in done]
        chain=build_chain()
        sem=asyncio.Semaphore(concurrency)
        with CARDS.open('a',encoding='utf-8') as out :
            for i in range(0,len(todo),200):
                batch=todo[i:i+200]
                for r in await asyncio.gather(*[_process(chain, sem, p) for p in batch]):
                    if r :
                        out.write(json.dumps(r, ensure_ascii=False) + "\n")
                        out.flush()
                        print(f"distilled {min(i + 200, len(todo))}/{len(todo)}")
                        
                        
if __name__=="__main__":
    getConceptCards()