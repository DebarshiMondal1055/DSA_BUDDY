"""Without this file you are guessing. Measure before you tune anything.

Gold set construction (eval/build_goldset.py writes data/goldset.json):
  1. Hand-label 60-100 pairs you know are conceptually twins (you have the CP
     background for this — it is the highest-quality signal you can get).
  2. Mine Codeforces editorial blogs for "similar problem" / "see also" links.
  3. Mine LeetCode's own "Similar Questions" section (same-platform, but it
     validates the concept-card representation independent of cross-platform).
  4. Use CSES topic sections as clusters: any two problems in the same CSES
     category are weakly positive.

Metrics: recall@10 is the one that matters for a "show me similar problems" UX.
"""
from __future__ import annotations
import json, math
from core.schema import DATA
from core.retrieve import SimilarProblemSearch


def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def evaluate(k: int = 10):
    gold = json.loads((DATA / "goldset.json").read_text())
    engine = SimilarProblemSearch()
    rec, rr, ndcg = [], [], []

    for case in gold:
        got = engine.search(case["query_url"], k=k, exclude_same_platform=False)
        ids = [r["problem_id"] for r in got["results"]]
        pos = set(case["positives"])

        rec.append(len(pos & set(ids)) / max(len(pos), 1))
        rr.append(next((1 / (i + 1) for i, p in enumerate(ids) if p in pos), 0.0))
        rels = [1 if p in pos else 0 for p in ids]
        ideal = sorted(rels, reverse=True)
        ndcg.append(dcg(rels) / dcg(ideal) if any(ideal) else 0.0)

    n = len(gold)
    print(f"n={n}  recall@{k}={sum(rec)/n:.3f}  MRR={sum(rr)/n:.3f}  nDCG@{k}={sum(ndcg)/n:.3f}")


ABLATIONS = """
Run each and record the numbers. This is your project's actual contribution:

  A. raw statement embedding                    <- baseline, will be weak
  B. statement + platform tags
  C. concept card only                          <- expect the big jump
  D. concept card + BM25 hybrid
  E. D + cross-encoder rerank
  F. E + difficulty-window filter

Report recall@10 for each. If C does not beat A by a wide margin, your
distillation prompt is leaking narrative — check the cards by hand.
"""

if __name__ == "__main__":
    evaluate()
    print(ABLATIONS)
