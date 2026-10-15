from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path so 'core' module can be imported regardless of execution location
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json, re, asyncio
from datasets import load_dataset
from core.schema import DATA, load_all, read_jsonl
from huggingface.chat_model import llm

chat_model = llm
SOLUTIONS = DATA / "solutions.jsonl"
LEETCODE = DATA / "leetcode.jsonl"

_AC = re.compile(r"\b(a[br]c\d{3}_[a-z]|agc\d{3}_[a-z])\b", re.I)
_CF = re.compile(r"(\d{3,4})\s*([A-Z]\d?)\b")

LANGUAGES = ("c++", "cpp", "java", "python", "python3")


def _pick(sols: dict | list, n: int = 2) -> list[str]:
    if isinstance(sols, dict):
        langs, srcs = sols.get("language", []), sols.get("solution", [])
        pairs = list(zip(langs, srcs))
    else:
        pairs = [(None, s) for s in (sols or [])]
    pairs.sort(
        key=lambda p: (
            LANGUAGES.index(str(p[0]).lower())
            if str(p[0]).lower() in LANGUAGES
            else 99,
            len(p[1]),
        )
    )
    return [s for _, s in pairs[:n] if s and len(s) < 12000]


# loading codeforces data
def codeforces_data(out) -> int:
    n = 0
    ds = load_dataset("open-r1/codeforces", split="train")
    for row in ds:
        cid, idx = row.get("contest_id"), row.get("index")
        if not cid or not idx:
            continue
        sols = _pick(
            row.get("generated_checker") and [] or row.get("solutions") or []
        )
        editorial = row.get("editorial")
        if not sols and not editorial:
            continue
        out.write(
            json.dumps(
                {
                    "problem_id": f"cf:{cid}/{idx}",
                    "editorial": editorial,
                    "solutions": sols,
                    "source": "open-r1/codeforces",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        n += 1
    return n


def _map_cc_id(name: str, source) -> str | None:
    if m := _AC.search(name):
        return f"ac:{m.group(1).lower()}"
    if m := _CF.search(name):
        return f"cf:{m.group(1)}/{m.group(2)}"
    return None


# for atcoder contest
def atcoder_data(out) -> int:
    ds = load_dataset("deepmind/code_contests", split="train")
    n = 0
    for row in ds:
        pid = _map_cc_id(row.get("name", ""), row.get("source"))
        if not pid:
            continue
        sols = _pick(row.get("solutions") or {})
        if not sols:
            continue
        out.write(
            json.dumps(
                {
                    "problem_id": pid,
                    "editorial": None,
                    "solutions": sols,
                    "source": "code_contests",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        n += 1
    return n


SYNTH_PROMPT = (
    "Write the intended reference solution for this problem in C++. Output only "
    "code, no explanation. Use the standard competitive-programming approach that "
    "fits the stated constraints — not a brute force."
)

_FENCE = re.compile(
    r"```(?:[\w+#.-]+)?\s*\n(.*?)(?:```|$)",
    re.S,
)


def _strip_fences(text: str) -> str:
    """Small models often wrap code in ``` fences or leave the last one unclosed."""
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _extract_text(res) -> str:
    """Extract generated text string safely from various model/pipeline output formats."""
    if hasattr(res, "content"):
        content = res.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)
    if isinstance(res, str):
        return res
    if isinstance(res, list) and len(res) > 0:
        item = res[0]
        if isinstance(item, dict):
            gen = item.get("generated_text", "")
            if isinstance(gen, list) and len(gen) > 0:
                last = gen[-1]
                if isinstance(last, dict) and "content" in last:
                    return last["content"]
                return str(last)
            return str(gen)
        return str(item)
    return str(res)


async def synth_reference(
    problems: list[dict],
    chat_model=llm,
    concurrency: int = 1,
    retries: int = 3,
    backoff: float = 2.0,
    out_file: Path | None = None,
    solved_offset: int = 0,
    total_dataset_size: int | None = None,
) -> list[dict]:
    """Generate reference solutions for problems and stream results directly to out_file."""
    if not problems:
        return []

    sem = asyncio.Semaphore(concurrency)
    failures = 0
    successes = 0
    total = len(problems)

    async def one(p: dict):
        nonlocal failures, successes
        pid = p.get("problem_id", "unknown")
        title = p.get("title", "")
        stmt = p.get("statement", "")[:5000]

        messages = [
            {"role": "system", "content": SYNTH_PROMPT},
            {"role": "user", "content": f"Title: {title}\n\n{stmt}"},
        ]

        async with sem:
            for attempt in range(retries):
                try:
                    try:
                        res = await chat_model.ainvoke(messages)
                    except Exception:
                        prompt = f"{SYNTH_PROMPT}\n\nTitle: {title}\n\n{stmt}"
                        res = await chat_model.ainvoke(prompt)

                    text = _extract_text(res)
                    code = _strip_fences(text)
                    if len(code) < 40:
                        raise ValueError(
                            f"model returned empty or too-short code ({len(code)} chars)"
                        )

                    successes += 1
                    if total_dataset_size is not None:
                        print(
                            f"[{successes}/{total}] (overall: {solved_offset + successes}/{total_dataset_size}) synthesized {pid}: {title}"
                        )
                    else:
                        print(f"[{successes}/{total}] synthesized {pid}: {title}")
                    return {
                        "problem_id": pid,
                        "editorial": None,
                        "solutions": [code],
                        "source": "synth",
                    }
                except Exception as e:
                    if attempt == retries - 1:
                        failures += 1
                        print(f"synth fail {pid}: {type(e).__name__}: {e}")
                        return None
                    await asyncio.sleep(backoff * (2 ** attempt))

    tasks = [asyncio.create_task(one(p)) for p in problems]
    results: list[dict] = []

    if out_file:
        with out_file.open("a", encoding="utf-8") as f:
            for fut in asyncio.as_completed(tasks):
                r = await fut
                if r:
                    results.append(r)
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
    else:
        for fut in asyncio.as_completed(tasks):
            r = await fut
            if r:
                results.append(r)

    print(f"synth complete: {len(results)} ok, {failures} failed")
    return results


async def generate_leetcode_solutions(
    limit: int | None = None,
    concurrency: int = 1,
    chat_model=llm,
    out_file: Path = SOLUTIONS,
) -> int:
    """Load leetcode.jsonl, skip already synthesized problems, and run synth_reference."""
    if not LEETCODE.exists():
        print(f"Error: {LEETCODE} does not exist.")
        return 0

    leetcode_problems = read_jsonl(LEETCODE)
    if not leetcode_problems:
        print(f"No problems found in {LEETCODE}")
        return 0

    leetcode_ids = {
        p.get("problem_id") for p in leetcode_problems if p.get("problem_id")
    }

    done_lc_ids = set()
    if out_file.exists():
        with out_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        r = json.loads(line)
                        pid = r.get("problem_id")
                        # Only count as solved if it belongs to LeetCode and has non-empty solutions
                        if pid and pid in leetcode_ids and r.get("solutions"):
                            done_lc_ids.add(pid)
                    except Exception:
                        pass

    todo = [p for p in leetcode_problems if p.get("problem_id") not in done_lc_ids]
    print(
        f"LeetCode total: {len(leetcode_problems)}, already solved: {len(done_lc_ids)}, to synthesize: {len(todo)}"
    )

    if not todo:
        print("All LeetCode problems already have solutions in solutions.jsonl!")
        return 0

    if limit == 0:
        print("Limit is 0; skipping synthesis.")
        return 0

    if limit is not None and limit > 0:
        todo = todo[:limit]
        print(f"Limit applied: synthesizing next {len(todo)} problem(s).")

    new_sols = await synth_reference(
        todo,
        chat_model=chat_model,
        concurrency=concurrency,
        out_file=out_file,
        solved_offset=len(done_lc_ids),
        total_dataset_size=len(leetcode_problems),
    )
    print(f"Saved {len(new_sols)} solutions to {out_file}")
    return len(new_sols)


def process_datasets(out_file: Path = SOLUTIONS) -> None:
    mode = "a" if out_file.exists() else "w"
    with out_file.open(mode, encoding="utf-8") as out:
        print("open-r1/codeforces:", codeforces_data(out))
        print("code_contests:", atcoder_data(out))
    print(f"wrote datasets to {out_file}")


def process():
    """Default entrypoint: synthesize LeetCode solutions."""
    asyncio.run(generate_leetcode_solutions())


def __getattr__(name: str):
    if name in ("generator", "chat_model", "model"):
        return llm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate solutions for problems")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of problems to synthesize (e.g. --limit 5)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent generations (default 1 for local pipeline)",
    )
    parser.add_argument(
        "--datasets",
        action="store_true",
        help="Ingest Codeforces & AtCoder datasets instead of LeetCode synth",
    )
    args = parser.parse_args()

    if args.datasets:
        process_datasets()
    else:
        asyncio.run(
            generate_leetcode_solutions(
                limit=args.limit, concurrency=args.concurrency
            )
        )
