import re
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.retrieve import SimilarProblemSearch
from fastapi.responses import JSONResponse

app = FastAPI(title="DSA Buddy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = SimilarProblemSearch()


def _build_url(plat: str | None, p_id: str | None) -> str | None:
    if not plat or not p_id:
        return None
    # Strip prefix if stored like "leetcode:two-sum" or "cf:1850A"
    raw_id = str(p_id).split(":", 1)[-1]
    if plat == "leetcode":
        return f"https://leetcode.com/problems/{raw_id}/"
    if plat == "codeforces":
        # e.g., "1850A" -> contest 1850, index A
        match = re.match(r"^(\d+)([A-Za-z]\d*)$", raw_id)
        if match:
            return f"https://codeforces.com/problemset/problem/{match.group(1)}/{match.group(2)}"
    if plat == "atcoder":
        # e.g., "abc100_a" -> contest abc100, task abc100_a
        contest = raw_id.split("_")[0]
        return f"https://atcoder.jp/contests/{contest}/tasks/{raw_id}"
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


class Query(BaseModel):
    query: str                        # problem URL, or pasted statement
    solution_code: str | None = None  # optional: your AC code -> exact method match
    k: int = 12
    mode: str = "both"                # both | method | concept
    per_platform_min: int = 3
    platform: str | None = None       # guarantees CF + LC + AC coverage


@app.post("/similar")
def similar(q: Query):
    result = engine.search(
        q.query,
        k=q.k,
        mode=q.mode,
        solution_code=q.solution_code,
        per_platform_min=q.per_platform_min,
        platform=q.platform,
    )

    for r in result["results"]:
        if not r.get("url"):
            r["url"] = _build_url(plat=r.get("platform"), p_id=r.get("problem_id"))

    return JSONResponse(content={'data': result, "message": "Problems retireved successfully"}, status_code=200)


@app.get("/ladder")
def ladder(method_key: str, around: int | None = None, n: int = 12):
    rows = engine.ladder(method_key, around=around, n=n)
    for r in rows:
        if not r.get("url"):
            r["url"] = _build_url(plat=r.get("platform"), p_id=r.get("problem_id"))
    return rows
