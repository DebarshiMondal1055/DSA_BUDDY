"""Codeforces: official API gives metadata+tags+rating; statements need scraping."""
from __future__ import annotations
import sys
from pathlib import Path

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


def fetch_index() -> list[dict]:
    r = requests.get(API, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()["result"]["problems"]


def fetch_statement(contest_id: int, index: str) -> str | None:
    key = CACHE / f"{contest_id}{index}.html"
    if key.exists():
        html = key.read_text(encoding="utf-8")
    else:
        url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code != 200:
            return None
        html = r.text
        key.write_text(html, encoding="utf-8")
        time.sleep(1.2)                      # be polite or get banned
    soup = BeautifulSoup(html, "lxml")
    node = soup.select_one("div.problem-statement")
    if not node:
        return None
    for junk in node.select("div.sample-tests, div.header"):
        junk.decompose()
    return clean_text(node.get_text("\n"))


def main(limit: int | None = None):
    out = []
    for i, p in enumerate(fetch_index()):
        if limit and i >= limit:
            break
        cid, idx = p.get("contestId"), p.get("index")
        if cid is None:
            continue
        stmt = fetch_statement(cid, idx)
        if not stmt or len(stmt) < 120:
            continue
        rating = p.get("rating")
        out.append(Problem(
            problem_id=f"cf:{cid}/{idx}",
            platform="codeforces",
            title=p.get("name", ""),
            url=f"https://codeforces.com/problemset/problem/{cid}/{idx}",
            statement=stmt,
            tags=p.get("tags", []),
            difficulty=normalize_difficulty("codeforces", rating),
            raw_difficulty=rating,
        ))
        if len(out) % 200 == 0:
            print(f"codeforces: {len(out)}")
    write_jsonl(DATA / "codeforces.jsonl", out)
    print(f"codeforces: wrote {len(out)}")


if __name__ == "__main__":
    main()
