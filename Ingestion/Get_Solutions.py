from __future__ import annotations
import json, re, asyncio
from datasets import load_dataset
from core.schema import DATA,load_all

SOLUTIONS=DATA/'solutions.jsonl'

_AC = re.compile(r"\b(a[br]c\d{3}_[a-z]|agc\d{3}_[a-z])\b", re.I)
_CF = re.compile(r"(\d{3,4})\s*([A-Z]\d?)\b")
 

LANGUAGES={'c++','cpp','java','python','python3'}

def _pick(sols: dict | list, n: int = 2) -> list[str]:
    
    if isinstance(sols, dict):                    
        langs, srcs = sols.get("language", []), sols.get("solution", [])
        pairs = list(zip(langs, srcs))
    else:
        pairs = [(None, s) for s in (sols or [])]
    pairs.sort(key=lambda p: (LANGUAGES.index(str(p[0]).lower()) if str(p[0]).lower() in LANGUAGES else 99, len(p[1])))
    return [s for _, s in pairs[:n] if s and len(s) < 12000]



#loading codeforces data
def codeforces_data(out)-> int:
    n=0
    ds=load_dataset("open-r1/codeforces", split="train")
    for row in ds:
        cid, idx = row.get("contest_id"), row.get("index")
        if not cid or not idx:
            continue
        sols = _pick(row.get("generated_checker") and [] or row.get("solutions") or [])
        editorial = row.get("editorial")
        if not sols and not editorial:
            continue
        out.write(json.dumps({
            "problem_id": f"cf:{cid}/{idx}",
            "editorial": editorial,
            "solutions": sols,
            "source": "open-r1/codeforces",
        }, ensure_ascii=False) + "\n")
        n += 1
    return n



def _map_cc_id(name: str, source) -> str | None:
    if m := _AC.search(name):
        return f"ac:{m.group(1).lower()}"
    if m := _CF.search(name):
        return f"cf:{m.group(1)}/{m.group(2)}"
    return None
 


# for atcoder contest

def atcoder_data(out)-> int:
    ds = load_dataset("deepmind/code_contests", split="train")
    n = 0
    for row in ds:
        pid = _map_cc_id(row.get("name", ""), row.get("source"))
        if not pid:
            continue
        sols = _pick(row.get("solutions") or {})
        if not sols:
            continue
        out.write(json.dumps({
            "problem_id": pid, 
            "editorial": None,
            "solutions": sols, 
            "source": "code_contests",
        }, ensure_ascii=False) + "\n")
        n += 1
    return n




SYNTH_PROMPT = (
    "Write the intended reference solution for this problem in C++. Output only "
    "code, no explanation. Use the standard competitive-programming approach that "
    "fits the stated constraints — not a brute force."
)


async def synth_reference(problems, model="openai:gpt-5-mini", concurrency=8):
    import asyncio
    from langchain.chat_models import init_chat_model
    llm = init_chat_model(model, temperature=0)
    sem = asyncio.Semaphore(concurrency)
 
    async def one(p):
        async with sem:
            try:
                r = await llm.ainvoke(
                    f"{SYNTH_PROMPT}\n\nTitle: {p['title']}\n\n{p['statement'][:5000]}")
                return {"problem_id": p["problem_id"], "editorial": None,
                        "solutions": [r.content], "source": "synth"}
            except Exception:
                return None
 
    return [r for r in await asyncio.gather(*[one(p) for p in problems]) if r]
 
 
def process():
    with SOLUTIONS.open("w", encoding="utf-8") as out:
        print("open-r1/codeforces:", codeforces_data(out))
        print("code_contests:", atcoder_data(out))
    print(f"wrote {SOLUTIONS}")
 
 
if __name__ == "__main__":
    process()
 
    
