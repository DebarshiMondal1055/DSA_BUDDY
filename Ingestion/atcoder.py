from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time, requests, json, re
from bs4 import BeautifulSoup
from core.schema import Problem, DATA, clean_text, normalize_difficulty, write_jsonl

BASE = "https://kenkoooo.com/atcoder/resources"
UA = {"User-Agent": "dsa-similarity-research/0.1 (educational; contact: you@example.com)"}
CACHE = DATA / "html" / "ac"
CACHE.mkdir(parents=True, exist_ok=True)

_PATTERN = re.compile(r"^ac:([a-zA-Z0-9_-]+)$", re.IGNORECASE)
_ATCODER = _PATTERN  # Backwards compatibility alias
SOLUTIONS = DATA / "solutions.jsonl"
_TARGET_IDS: set[str] | None = None


def get_target_problem_ids(solutions_path: Path = SOLUTIONS) -> set[str]:
    """Load and cache the set of problem_ids from solutions.jsonl matching ac:<task_id>."""
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


def fetch_index() -> tuple[list[dict], dict[str, dict]]:
    """Fetch AtCoder problems and problem models from Kenkoooo API, with local disk caching."""
    prob_cache = CACHE / "kenkoooo_problems.json"
    model_cache = CACHE / "kenkoooo_models.json"

    problems, models = None, None
    if prob_cache.exists() and model_cache.exists():
        try:
            problems = json.loads(prob_cache.read_text(encoding="utf-8"))
            models = json.loads(model_cache.read_text(encoding="utf-8"))
        except Exception:
            problems, models = None, None

    if problems is None or models is None:
        try:
            r_prob = requests.get(f"{BASE}/problems.json", headers=UA, timeout=60)
            r_prob.raise_for_status()
            problems = r_prob.json()
            prob_cache.write_text(r_prob.text, encoding="utf-8")

            r_models = requests.get(f"{BASE}/problem-models.json", headers=UA, timeout=60)
            r_models.raise_for_status()
            models = r_models.json()
            model_cache.write_text(r_models.text, encoding="utf-8")
        except requests.exceptions.RequestException as e:
            if problems is not None and models is not None:
                return problems, models
            print(f"Warning: Failed to fetch from Kenkoooo ({e}).", flush=True)
            return (problems or []), (models or {})

    return problems, models


def fetch_statement(contest_id: str, problem_id: str, check_target: bool = True) -> str | None:
    pid = f"ac:{problem_id}"
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
        if check_target and pid not in get_target_problem_ids():
            return None

        url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}?lang=en"
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            html = r.text
        except requests.exceptions.RequestException as e:
            print(f"Failed {contest_id}/{problem_id}: {e}", flush=True)
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


def main(limit: int | None = None, all_problems: bool = False, keep_existing: bool = False):
    out: list[Problem] = []
    outfile = DATA / "atcoder.jsonl"
    solutions_file = SOLUTIONS

    seen_ids: set[str] = set()
    if keep_existing and outfile.exists():
        from core.schema import read_jsonl
        for p_dict in read_jsonl(outfile):
            pid = p_dict["problem_id"]
            seen_ids.add(pid)
            out.append(Problem(**p_dict))
        print(f"Loaded {len(out)} existing problems from {outfile.name}", flush=True)

    problems, models = fetch_index()
    print(f"Fetched index with {len(problems)} problems.", flush=True)
    api_map: dict[str, dict] = {p["id"]: p for p in problems if "id" in p}

    if not all_problems and solutions_file.exists():
        target_ids = get_target_problem_ids(solutions_file)
        print(f"Target AtCoder problems in {solutions_file.name}: {len(target_ids)}", flush=True)

        with open(solutions_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if limit and len(out) >= limit:
                    break
                if not line.strip():
                    continue
                try:
                    problem_row = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON on line {line_num}", flush=True)
                    continue

                pid = problem_row.get("problem_id") or ""
                match = _PATTERN.match(pid)
                if not match:
                    continue

                raw_id = match.group(1)
                formatted_pid = f"ac:{raw_id}"

                if formatted_pid in seen_ids:
                    continue
                seen_ids.add(formatted_pid)

                meta = api_map.get(raw_id, {})
                contest_id = meta.get("contest_id") or raw_id.split("_")[0]

                stmt = fetch_statement(contest_id, raw_id)
                if not stmt or len(stmt) < 120:
                    continue

                title = meta.get("title") or meta.get("name", "")
                if not title:
                    key = CACHE / f"{raw_id}.html"
                    if key.exists():
                        try:
                            soup = BeautifulSoup(key.read_text(encoding="utf-8", errors="ignore"), "lxml")
                            t_node = soup.select_one("span.h2") or soup.select_one("h2") or soup.title
                            if t_node:
                                title = clean_text(t_node.get_text().replace("Editorial", "").strip())
                        except Exception:
                            pass
                if not title:
                    title = raw_id

                diff = (models.get(raw_id) or {}).get("difficulty")
                out.append(Problem(
                    problem_id=formatted_pid,
                    platform="atcoder",
                    title=title,
                    url=f"https://atcoder.jp/contests/{contest_id}/tasks/{raw_id}",
                    statement=stmt,
                    tags=[],                       # AtCoder has none — the distiller supplies them
                    difficulty=normalize_difficulty("atcoder", diff),
                    raw_difficulty=diff,
                ))
                if len(out) == 1 or len(out) % 20 == 0:
                    write_jsonl(outfile, out)
                if len(out) % 200 == 0 and len(out) > 0:
                    print(f"atcoder: {len(out)}", flush=True)
    else:
        for i, p in enumerate(problems):
            if limit and len(out) >= limit:
                break
            raw_id = p.get("id")
            if not raw_id:
                continue
            formatted_pid = f"ac:{raw_id}"
            if formatted_pid in seen_ids:
                continue
            seen_ids.add(formatted_pid)

            contest_id = p.get("contest_id") or raw_id.split("_")[0]
            stmt = fetch_statement(contest_id, raw_id, check_target=False)
            if not stmt or len(stmt) < 120:
                continue
            diff = (models.get(raw_id) or {}).get("difficulty")
            title = p.get("title") or p.get("name") or raw_id
            out.append(Problem(
                problem_id=formatted_pid,
                platform="atcoder",
                title=title,
                url=f"https://atcoder.jp/contests/{contest_id}/tasks/{raw_id}",
                statement=stmt,
                tags=[],
                difficulty=normalize_difficulty("atcoder", diff),
                raw_difficulty=diff,
            ))
            if len(out) == 1 or len(out) % 20 == 0:
                write_jsonl(outfile, out)
            if len(out) % 200 == 0 and len(out) > 0:
                print(f"atcoder: {len(out)}", flush=True)

    write_jsonl(outfile, out)
    print(f"atcoder: wrote {len(out)} problems to {outfile}", flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest AtCoder problems matching solutions.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of problems to ingest")
    parser.add_argument("--all", action="store_true", help="Ingest all AtCoder problems from index instead of filtering by solutions.jsonl")
    parser.add_argument("--keep-existing", action="store_true", help="Keep problems already present in atcoder.jsonl")
    args = parser.parse_args()
    main(limit=args.limit, all_problems=args.all, keep_existing=args.keep_existing)
