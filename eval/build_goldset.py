"""Build data/goldset.json from hand-labelled twins.

Input: data/gold_pairs.tsv, one line per query problem:

    # query_id <TAB> comma-separated positive ids
    cf:461/B    lc:2477,ac:abc222_f
    lc:2213     cf:380/C

Every id must exist in the ingested corpus (data/*.jsonl); unknown ids are
reported and skipped so a typo doesn't silently become a "miss" in eval.

    python -m eval.build_goldset               # one case per line
    python -m eval.build_goldset --symmetric   # also add the reverse direction
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from core.schema import DATA, load_all

PAIRS = DATA / "gold_pairs.tsv"
OUT = DATA / "goldset.json"


def parse_pairs(path=PAIRS) -> dict[str, list[str]]:
    pairs: dict[str, list[str]] = defaultdict(list)
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            print(f"line {n}: expected 'query_id<TAB>pos1,pos2' — skipped")
            continue
        q = parts[0].strip()
        for p in parts[1].split(","):
            if p.strip() and p.strip() not in pairs[q]:
                pairs[q].append(p.strip())
    return pairs


def build(symmetric: bool = False) -> list[dict]:
    corpus = {p["problem_id"]: p for p in load_all()}
    pairs = parse_pairs()

    if symmetric:                       
        for q, pos in list(pairs.items()):
            for p in pos:
                if q not in pairs[p]:
                    pairs[p].append(q)

    gold = []
    for q, pos in pairs.items():
        if q not in corpus:
            print(f"query {q}: not in corpus — skipped")
            continue
        good = [p for p in pos if p in corpus and p != q]
        for p in set(pos) - set(good) - {q}:
            print(f"query {q}: positive {p} not in corpus — dropped")
        if good:
            gold.append({"query_id": q, "query_url": corpus[q]["url"], "positives": good})
    return gold


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symmetric", action="store_true")
    a = ap.parse_args()
    g = build(a.symmetric)
    OUT.write_text(json.dumps(g, indent=1), encoding="utf-8")
    print(f"wrote {len(g)} cases -> {OUT}")