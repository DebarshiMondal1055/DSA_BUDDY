from __future__ import annotations
import os,json,re,pathlib
from dataclasses import dataclass, field,asdict

DATA=pathlib.Path(__file__).resolve().parent.parent/"data"
    
DATA.mkdir(exist_ok=True)

@dataclass

class Problem :
    problem_id: str
    title : str
    platform : str
    url : str
    statement : str
    difficulty : int | None = None
    raw_difficulty : str | int | None= None
    tags : list[str]=field(default_factory=list)
    samples: list[str]=field(default_factory=list)
    
    def to_json()->str :
        return json.dumps(asdict(self),ensure_ascii=True)
    
    
    
    
def normalise_difficulty(platform : str,raw) -> float :
    if raw is None:
        return None
    if platform == "codeforces":                 # 800..3500
        return max(0, min(100, round((raw - 800) / 27)))
    if platform == "atcoder":                    # kenkoooo difficulty, ~0..3500
        return max(0, min(100, round(max(raw, 0) / 35)))
    if platform == "leetcode":
        return {"Easy": 15, "Medium": 45, "Hard": 75}.get(raw)
    return None

_WS = re.compile(r"[ \t]+")
_NL = re.compile(r"\n{3,}")
 

def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ").replace("\u2212", "-")
    s = _WS.sub(" ", s)
    return _NL.sub("\n\n", s).strip()


def write_jsonl(path: pathlib.Path, problems) -> None:
    with path.open("w", encoding="utf-8") as f:
        for p in problems:
            f.write(p.to_json() + "\n")
 
 

def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
 
 
def load_all() -> list[dict]:
    out = []
    for name in ("codeforces.jsonl", "leetcode.jsonl", "atcoder.jsonl"):
        out += read_jsonl(DATA / name)
    return out