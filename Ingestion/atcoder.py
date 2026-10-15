from __future__ import annotations
import sys
from pathlib import Path

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
    html = None

    if key.exists():
        try:
            cached_text = key.read_text(encoding="utf-8", errors="ignore")
            if "task-statement" in cached_text or "lang-en" in cached_text:
                html = cached_text
            else:
                key.unlink(missing_ok=True)
        except Exception:
            key.unlink(missing_ok=True)

    if html is None:
        url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}?lang=en"
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            html = r.text
        except requests.exceptions.RequestException as e:
            print(f"Failed {contest_id}/{problem_id}: {e}")
            return None

        soup = BeautifulSoup(html, "lxml")
        node = soup.select_one("span.lang-en") or soup.select_one("#task-statement")
        if not node:
            return None

        key.write_text(html, encoding="utf-8")
        time.sleep(1.2)
    else:
        soup = BeautifulSoup(html, "lxml")
        node = soup.select_one("span.lang-en") or soup.select_one("#task-statement")
        if not node:
            key.unlink(missing_ok=True)
            return None

    for junk in node.select("div.part h3 + pre"):   # sample IO blocks
        junk.decompose()

    return clean_text(node.get_text("\n"))


def main(limit: int | None = None):
    problems, models = fetch_index()
    out = []
    outfile = DATA / "atcoder.jsonl"
    print(f"Fetched index with {len(problems)} problems.")

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
        if len(out) == 1 or len(out) % 20 == 0:
            write_jsonl(outfile, out)
        if len(out) % 200 == 0 and len(out) > 0:
            print(f"atcoder: {len(out)}")

    write_jsonl(outfile, out)
    print(f"atcoder: wrote {len(out)} problems to {outfile}")


if __name__ == "__main__":
    main()
