from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path so 'core' module can be imported regardless of execution location
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time, requests
from bs4 import BeautifulSoup
from core.schema import Problem, DATA, clean_text, normalize_difficulty, write_jsonl

BASE = "https://kenkoooo.com/atcoder/resources"
UA = {"User-Agent": "dsa-similarity-research/0.1 (educational; contact: you@example.com)"}
CACHE = DATA / "html" / "ac"
CACHE.mkdir(parents=True, exist_ok=True)


def fetch_index():
    problems = requests.get(f"{BASE}/problems.json", headers=UA, timeout=60).json()
    models = requests.get(f"{BASE}/problem-models.json", headers=UA, timeout=60).json()
    return problems, models


def fetch_statement(contest_id: str, problem_id: str) -> str | None:
    key = CACHE / f"{problem_id}.html"
    if key.exists():
        html = key.read_text(encoding="utf-8")
    else:
        url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}?lang=en"
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code != 200:
            return None
        html = r.text
        key.write_text(html, encoding="utf-8")
        time.sleep(1.2)
    soup = BeautifulSoup(html, "lxml")
    # AtCoder ships JA and EN side by side; take the English span
    node = soup.select_one("span.lang-en") or soup.select_one("#task-statement")
    if not node:
        return None
    for junk in node.select("div.part h3 + pre"):   # sample IO blocks
        junk.decompose()
    return clean_text(node.get_text("\n"))


def main(limit: int | None = None):
    problems, models = fetch_index()
    out = []
    for i, p in enumerate(problems):
        if limit and i >= limit:
            break
        pid = p["id"]
        stmt = fetch_statement(p["contest_id"], pid)
        if not stmt or len(stmt) < 120:
            continue
        diff = (models.get(pid) or {}).get("difficulty")
        out.append(Problem(
            problem_id=f"ac:{pid}",
            platform="atcoder",
            title=p.get("title") or p.get("name", ""),
            url=f"https://atcoder.jp/contests/{p['contest_id']}/tasks/{pid}",
            statement=stmt,
            tags=[],                       # AtCoder has none — the distiller supplies them
            difficulty=normalize_difficulty("atcoder", diff),
            raw_difficulty=diff,
        ))
        if len(out) % 200 == 0:
            print(f"atcoder: {len(out)}")
    write_jsonl(DATA / "atcoder.jsonl", out)
    print(f"atcoder: wrote {len(out)}")


if __name__ == "__main__":
    main()
