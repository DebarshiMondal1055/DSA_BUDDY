from pydantic import BaseModel,Field
from fastapi import FastAPI
from core.retrieve import SimilarProblemSearch

app=FastAPI()
engine=SimilarProblemSearch()

@app.get("/health")
def health():
    return {"status": "ok"}

class Query(BaseModel):
    query: str                        # problem URL, or pasted statement
    solution_code: str | None = None  # optional: your AC code -> exact method match
    k: int = 12
    mode: str = "both"                # both | method | concept
    per_platform_min: int = 3         # guarantees CF + LC + AC coverage



@app.post('/similar')

def similar(q:Query):
    return engine.search(q.query, k=q.k, mode=q.mode,
                         solution_code=q.solution_code,
                         per_platform_min=q.per_platform_min)



@app.get("/ladder")
def ladder(method_key: str, around: int | None = None, n: int = 12):
    return engine.ladder(method_key, around=around, n=n)


