"""Codeforces: official API gives metadata+tags+rating; statements need scraping."""
from __future__ import annotations
import sys
from pathlib import Path
import json,re

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time, pathlib, requests
from bs4 import BeautifulSoup
from core.schema import Problem, DATA, clean_text, normalize_difficulty, write_jsonl

API = "https://codeforces.com/api/problemset.problems"
UA = {"User-Agent": "dsa-similarity-research/0.1 (educational; contact: you@example.com)"}
CACHE = DATA / "html" / "cf"
CACHE.mkdir(parents=True, exist_ok=True)

_PATTERN = re.compile(r"^cf:(\d+)/([A-Z]\d*)$", re.IGNORECASE)
SOLUTIONS = DATA / "solutions.jsonl"
_TARGET_IDS: set[str] | None = None


def get_target_problem_ids(solutions_path: Path = SOLUTIONS) -> set[str]:
    """Load and cache the set of problem_ids from solutions.jsonl matching cf:<Number>/<Letter>."""
    global _TARGET_IDS
    if _TARGET_IDS is None:
        _TARGET_IDS = set()
        if solutions_path.exists():
            with solutions_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        pid = row.get("problem_id", "")
                        if pid and _PATTERN.match(pid):
                            _TARGET_IDS.add(pid)
                    except Exception:
                        continue
    return _TARGET_IDS


def fetch_index() -> list[dict]:
    r = requests.get(API, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()["result"]["problems"]


def fetch_statement(contest_id: int, index: str, check_target: bool = True) -> str | None:
    index = index.upper()
    pid = f"cf:{contest_id}/{index}"
    key = CACHE / f"{contest_id}{index}.html"
    html = None

    if key.exists():
        try:
            cached_text = key.read_text(encoding="utf-8", errors="ignore")
            if "problem-statement" in cached_text:
                html = cached_text
            else:
                key.unlink(missing_ok=True)
        except Exception:
            key.unlink(missing_ok=True)

    if html is None:
        if check_target and pid not in get_target_problem_ids():
            return None

        url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            html = r.text
        except requests.exceptions.RequestException as e:
            print(f"Failed {contest_id}/{index}: {e}")
            return None

        soup = BeautifulSoup(html, "lxml")
        node = soup.select_one("div.problem-statement")
        if not node:
            return None

        key.write_text(html, encoding="utf-8")
        time.sleep(1.2)
    else:
        soup = BeautifulSoup(html, "lxml")
        node = soup.select_one("div.problem-statement")
        if not node:
            key.unlink(missing_ok=True)
            return None

    for junk in node.select("div.sample-tests, div.header"):
        junk.decompose()

    return clean_text(node.get_text("\n"))


def main(limit: int | None = None):
    out = []
    outfile = DATA / "codeforces.jsonl"
    solutions_file = SOLUTIONS

    if not solutions_file.exists():
        print(f"Error: {solutions_file} does not exist.")
        return

    problems = fetch_index()
    print(f"Fetched index with {len(problems)} problems.")
    api_map: dict[tuple[int, str], dict] = {}
    for p in problems:
        cid = p.get("contestId")
        idx = p.get("index")
        if cid is not None and idx is not None:
            api_map[(int(cid), str(idx).upper())] = p

    target_ids = get_target_problem_ids(solutions_file)
    print(f"Target Codeforces problems in {solutions_file.name}: {len(target_ids)}")

    seen_ids: set[str] = set()
    with open(solutions_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            if limit and len(out) >= limit:
                break
            if not line.strip():
                continue
            try:
                problem_row = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_num}")
                continue

            pid = problem_row.get("problem_id") or ""
            match = _PATTERN.match(pid)
            if not match:
                continue

            contest_id_str, idx_str = match.groups()
            contest_id = int(contest_id_str)
            index = idx_str.upper()
            formatted_pid = f"cf:{contest_id}/{index}"

            if formatted_pid in seen_ids:
                continue
            seen_ids.add(formatted_pid)

            stmt = fetch_statement(contest_id, index)
            if not stmt or len(stmt) < 120:
                continue

            meta = api_map.get((contest_id, index), {})
            title = meta.get("name", "")
            rating = meta.get("rating")
            tags = meta.get("tags", [])

            if not title:
                key = CACHE / f"{contest_id}{index}.html"
                if key.exists():
                    try:
                        soup = BeautifulSoup(key.read_text(encoding="utf-8", errors="ignore"), "lxml")
                        t_node = soup.select_one("div.header div.title") or soup.select_one("div.title")
                        if t_node:
                            title = re.sub(r"^[A-Za-z0-9]+\.\s*", "", t_node.get_text().strip())
                    except Exception:
                        pass

            out.append(Problem(
                problem_id=formatted_pid,
                platform="codeforces",
                title=title,
                url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
                statement=stmt,
                tags=tags,
                difficulty=normalize_difficulty("codeforces", rating),
                raw_difficulty=rating,
            ))
            if len(out) == 1 or len(out) % 20 == 0:
                write_jsonl(outfile, out)
            if len(out) % 200 == 0 and len(out) > 0:
                print(f"codeforces: {len(out)}")

    write_jsonl(outfile, out)
    print(f"codeforces: wrote {len(out)} problems to {outfile}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Codeforces problems matching solutions.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of problems to ingest")
    args = parser.parse_args()
    main(limit=args.limit)
