"""Solution corpus for the method view: ONE record per problem_id.

    {"problem_id": "cf:1388/D", "editorial": str | None, "solutions": [code, ...], "source": str}

Where each platform's data comes from
    Codeforces  open-r1/codeforces              authors' editorial (prose, ~60% of problems)
                open-r1/codeforces-submissions  real accepted human code (config selected_accepted)
    AtCoder     deepmind/code_contests          real accepted code, rows with source == ATCODER only
    LeetCode    LLM-written reference code, tagged source="synth" (there is no public source)

Usage
    python -m ingest.solutions --probe      # first: see how AtCoder rows map onto your ids
    python -m ingest.solutions --datasets   # Codeforces + AtCoder; safe to re-run, keeps synth records
    python -m ingest.solutions --limit 20   # LeetCode synthesis, resumable
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.chat_model import llm
chat_model = llm
from core.schema import DATA, read_jsonl

SOLUTIONS = DATA / "solutions.jsonl"
LEETCODE = DATA / "leetcode.jsonl"
ATCODER = DATA / "atcoder.jsonl"

PER_PROBLEM = 1                      # solutions kept per problem
MIN_CHARS, MAX_CHARS = 150, 12_000   # drop trivial and enormous submissions
ATCODER_SOURCE = 5                   # code_contests `source` label (1 CODECHEF, 2 CODEFORCES, ... 6 AIZU)

# code_contests stores language as an int: 1 PYTHON(2), 2 CPP, 3 PYTHON3, 4 JAVA
_CC_LANG_RANK = {2: 0, 4: 1, 3: 2, 1: 2}

_AC_ID = re.compile(r"\b((?:abc|arc|agc)\d{3}_[a-z])\b", re.I)
_FENCE = re.compile(r"```(?:[\w+#.-]+)?\s*\n(.*?)(?:```|$)", re.S)

SYNTH_PROMPT = (
    "Write the intended reference solution for this problem in C++. Output only "
    "code, no explanation. Use the standard competitive-programming approach that "
    "fits the stated constraints — not a brute force."
)


# ------------------------------------------------------------------ helpers
def _load(repo: str, split: str, config: str | None = None, columns: list[str] | None = None):
    """load_dataset, reading only `columns` when the installed `datasets` supports it.
    Projection matters: code_contests is 7.6 GB, mostly test cases we never use."""
    from datasets import load_dataset

    args = (repo, config) if config else (repo,)
    if columns:
        try:
            return load_dataset(*args, split=split, columns=columns)
        except Exception as e:
            print(f"  (column projection unavailable for {repo}: {type(e).__name__}; loading all columns)")
    return load_dataset(*args, split=split)


def _lang_rank(lang) -> int | None:
    """0 = C++, 1 = Java, 2 = Python; None = skip. Accepts code_contests ints and
    Codeforces strings such as 'GNU C++17', 'Java 8', 'PyPy 3-64'."""
    if isinstance(lang, int):
        return _CC_LANG_RANK.get(lang)
    s = str(lang).lower()
    if "c++" in s:
        return 0
    if s.startswith("java") and "script" not in s:
        return 1
    if s.startswith(("python", "pypy")):
        return 2
    return None


def _pick(pairs, n: int = PER_PROBLEM) -> list[str]:
    """Best `n` codes from (language, code) pairs: C++ > Java > Python, shorter first."""
    ranked = []
    for lang, code in pairs:
        rank = _lang_rank(lang)
        if rank is not None and code and MIN_CHARS <= len(code) <= MAX_CHARS:
            ranked.append((rank, len(code), code))
    ranked.sort(key=lambda t: t[:2])
    return [code for _, _, code in ranked[:n]]


# --------------------------------------------------------------- Codeforces
def collect_codeforces() -> dict[str, dict]:
    """Editorial from open-r1/codeforces + accepted code from open-r1/codeforces-submissions,
    merged into one record per problem. Alias copies (Div1/Div2 twins) share the record."""
    subs = defaultdict(list)
    for row in _load("open-r1/codeforces-submissions", "train", "selected_accepted",
                     columns=["problem_id", "source", "programmingLanguage"]):
        subs[row["problem_id"]].append((row["programmingLanguage"], row["source"]))

    records: dict[str, dict] = {}
    for split in ("train", "test"):
        for row in _load("open-r1/codeforces", split,
                         columns=["contest_id", "index", "aliases", "editorial"]):
            pid = f"{row['contest_id']}/{row['index']}"
            editorial = (row.get("editorial") or "").strip() or None
            code = _pick(subs.get(pid, []))
            if not code and not editorial:
                continue
            body = {"editorial": editorial, "solutions": code,
                    "source": "codeforces-submissions" if code else "codeforces-editorial"}
            for alias in [pid, *(row.get("aliases") or [])]:
                records.setdefault(f"cf:{alias}", {"problem_id": f"cf:{alias}", **body})

    n_code = sum(1 for r in records.values() if r["solutions"])
    print(f"codeforces: {len(records)} problems ({n_code} with code, "
          f"{len(records) - n_code} editorial only)")
    return records


# ------------------------------------------------------------------ AtCoder
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _atcoder_title_index() -> dict[str, str]:
    """normalised title -> problem_id for YOUR ingested AtCoder problems.
    Titles that occur more than once are dropped: precision over recall."""
    index, ambiguous = {}, set()
    for p in read_jsonl(ATCODER):
        key = _norm(re.sub(r"^[A-Z]\d?\s*[-.]\s*", "", p["title"]))   # strip 'A. ' prefix
        if key in index and index[key] != p["problem_id"]:
            ambiguous.add(key)
        index[key] = p["problem_id"]
    return {k: v for k, v in index.items() if k not in ambiguous}


def _atcoder_id(name: str, by_title: dict[str, str]) -> str | None:
    if m := _AC_ID.search(name):                       # name embeds 'abc123_d'
        return f"ac:{m.group(1).lower()}"
    tail = name.rsplit(" - ", 1)[-1]                   # '... Contest 120 - Apple Pie'
    return by_title.get(_norm(tail)) or by_title.get(_norm(name))


def _is_atcoder(source) -> bool:
    return source == ATCODER_SOURCE or str(source).upper() == "ATCODER"


def _atcoder_rows():
    return _load("deepmind/code_contests", "train", columns=["name", "source", "solutions"])


def collect_atcoder() -> dict[str, dict]:
    by_title = _atcoder_title_index()
    records, unmatched, seen = {}, [], 0
    for row in _atcoder_rows():
        if not _is_atcoder(row["source"]):             # never trust names across platforms
            continue
        seen += 1
        pid = _atcoder_id(row["name"], by_title)
        if pid is None:
            unmatched.append(row["name"])
            continue
        sols = row["solutions"] or {}
        code = _pick(zip(sols.get("language", []), sols.get("solution", [])))
        if code:
            records.setdefault(pid, {"problem_id": pid, "editorial": None,
                                     "solutions": code, "source": "code_contests"})
    print(f"atcoder: {seen} dataset rows, {len(records)} mapped to your ids, "
          f"{len(unmatched)} unmatched")
    for name in unmatched[:5]:
        print(f"   unmatched: {name!r}")
    return records


def probe_atcoder(n: int = 12) -> None:
    """Show what AtCoder rows look like and whether they map. Run this before --datasets."""
    by_title = _atcoder_title_index()
    print(f"your AtCoder problems indexed by unique title: {len(by_title)}")
    shown = 0
    for row in _atcoder_rows():
        if _is_atcoder(row["source"]) and shown < n:
            print(f"  {row['name']!r:70} -> {_atcoder_id(row['name'], by_title)}")
            shown += 1
    if not shown:
        print("no rows with source == ATCODER were found")


# ------------------------------------------------------------ write datasets
def write_datasets(path: Path = SOLUTIONS) -> None:
    """Rewrite dataset-derived records. Idempotent, and keeps synthetic records already
    in the file (the old append mode duplicated everything on every re-run)."""
    keep = [r for r in read_jsonl(path) if r.get("source") == "synth"]
    records = [*collect_codeforces().values(), *collect_atcoder().values()]
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in [*records, *keep]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)
    print(f"wrote {len(records)} dataset records + kept {len(keep)} synth -> {path}")


# --------------------------------------------------------- LeetCode synthesis
def _strip_fences(text: str) -> str:
    """Models often wrap code in ``` fences, or leave the last fence unclosed."""
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _text(res) -> str:
    """Reply text from a LangChain message (str or list of content blocks) or a plain str."""
    content = getattr(res, "content", res)
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)



async def synth_reference(problems: list[dict], llm=None, concurrency: int = 1,
                          retries: int = 3, backoff: float = 2.0,
                          out_file: Path | None = None) -> list[dict]:
    """LLM-written reference solutions, appended to out_file as each one finishes."""
    if not problems:
        return []
    if llm is None:
        llm = globals().get("llm")
    sem = asyncio.Semaphore(concurrency)
    total, done, failed = len(problems), 0, 0

    async def one(p: dict) -> dict | None:
        nonlocal done, failed
        pid = p.get("problem_id", "unknown")
        messages = [{"role": "system", "content": SYNTH_PROMPT},
                    {"role": "user",
                     "content": f"Title: {p.get('title', '')}\n\n{p.get('statement', '')[:5000]}"}]
        async with sem:
            for attempt in range(retries):
                try:
                    code = _strip_fences(_text(await llm.ainvoke(messages)))
                    if len(code) < 40:
                        raise ValueError(f"empty or too-short code ({len(code)} chars)")
                    done += 1
                    print(f"[{done}/{total}] {pid}")
                    return {"problem_id": pid, "editorial": None,
                            "solutions": [code], "source": "synth"}
                except Exception as e:
                    if attempt == retries - 1:
                        failed += 1
                        print(f"synth fail {pid}: {type(e).__name__}: {e}")
                        return None
                    await asyncio.sleep(backoff * 2 ** attempt)

    tasks = [asyncio.create_task(one(p)) for p in problems]
    results: list[dict] = []
    sink = out_file.open("a", encoding="utf-8") if out_file else None
    try:
        for fut in asyncio.as_completed(tasks):
            if r := await fut:
                results.append(r)
                if sink:
                    sink.write(json.dumps(r, ensure_ascii=False) + "\n")
                    sink.flush()
    finally:
        if sink:
            sink.close()
    print(f"synth complete: {len(results)} ok, {failed} failed")
    return results


async def generate_leetcode_solutions(limit: int | None = None, concurrency: int = 1,
                                      llm=None, out_file: Path = SOLUTIONS) -> int:
    """Synthesise solutions for LeetCode problems that have none yet. Resumable."""
    problems = read_jsonl(LEETCODE)
    if not problems:
        print(f"No problems found in {LEETCODE}")
        return 0
    have = {r["problem_id"] for r in read_jsonl(out_file) if r.get("solutions")}
    todo = [p for p in problems if p["problem_id"] not in have]
    print(f"LeetCode: {len(problems)} total, {len(problems) - len(todo)} done, {len(todo)} to do")
    if limit is not None:
        todo = todo[:limit]
    new = await synth_reference(todo, llm=llm, concurrency=concurrency, out_file=out_file)
    return len(new)


# Thin wrappers so existing callers keep working.
def process_datasets(out_file: Path = SOLUTIONS) -> None:
    write_datasets(out_file)


def process() -> None:
    asyncio.run(generate_leetcode_solutions())


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the solution corpus")
    ap.add_argument("--datasets", action="store_true", help="Codeforces + AtCoder datasets")
    ap.add_argument("--probe", action="store_true", help="show how AtCoder rows map to your ids")
    ap.add_argument("--limit", type=int, default=None, help="max LeetCode problems to synthesise")
    ap.add_argument("--concurrency", type=int, default=1)
    args = ap.parse_args()

    if args.probe:
        probe_atcoder()
    elif args.datasets:
        write_datasets()
    else:
        asyncio.run(generate_leetcode_solutions(args.limit, args.concurrency))


if __name__ == "__main__":
    main()