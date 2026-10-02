from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path so 'core' module can be imported regardless of execution location
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from core.schema import DATA,load_all
from core.Distillation import CARDS,card_to_text
from core.MethodCard import METHODS,method_to_text
import json,re
import pickle

import os

COLLECTION = "dsa_problems"
QDRANT_URL = "http://localhost:6333"
DIM = 1536

def get_embeddings():
    key = os.getenv("OPENAI_API_KEY") or "sk-dummy"
    return OpenAIEmbeddings(model="text-embedding-3-small", dimensions=DIM, api_key=key)



def _load(path):
    if not path.exists():
        return {}
    with path.open("r",encoding='utf-8') as f:
        return {json.loads(l)['problem_id']:json.loads(l) for l in f if l.strip()}
    
def build_records():
    problems={p['problem_id']:p for p in load_all()}
    cards,methods=_load(CARDS),_load(METHODS) 
    records=[]
    for pid,p in problems.items():

        c=(cards.get(pid) or {}).get("card")
        if not c :
            continue
        m_rec=methods.get(pid)
        m=(m_rec or {}).get("method")
        
        records.append({
            "problem_id": pid,
            "statement_text": card_to_text(p["title"], p["platform"], c),
            "method_text": method_to_text(p["title"], p["platform"], m) if m else None,
            "payload": {
                "problem_id": pid,
                "platform": p["platform"],
                "title": p["title"],
                "url": p["url"],
                "difficulty": p.get("difficulty") if p.get("difficulty") is not None else -1,
                "core_technique": c["core_technique"],
                "concept_tags": c.get("canonical_tags") or [],
                "platform_tags": p.get("tags") or [],
                "reduction": c["reduction"],
                "complexity": c["complexity"],
                # method side
                "has_method": bool(m),
                "method_keys": (m or {}).get("method_keys", []),
                "primitives": (m or {}).get("primitives", []),
                "state_signature": (m or {}).get("state_signature"),
                "steps": (m or {}).get("steps"),
                "transferable_skill": (m or {}).get("transferable_skill"),
                "fingerprint": (m_rec or {}).get("fingerprint", {}),
                "sol_source": (m_rec or {}).get("sol_source"),
            },
        })
    return records


def main(batch: int =128):
    records=build_records()
    nm=sum(1 for r in records if r["method_text"])
    print(f"{len(records)} problems, {nm} with a method view")
    model = get_embeddings()
    client = QdrantClient(url=QDRANT_URL, timeout=120)

    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION,
        vectors_config={
            "statement": qm.VectorParams(size=DIM, distance=qm.Distance.COSINE),
            "method":    qm.VectorParams(size=DIM, distance=qm.Distance.COSINE),
        },
    )
    for field, schema in [("platform", "keyword"), ("concept_tags", "keyword"),
                          ("method_keys", "keyword"), ("primitives", "keyword"),
                          ("difficulty", "integer"), ("has_method", "bool"),
                          ("problem_id", "keyword")]:
        client.create_payload_index(COLLECTION, field_name=field, field_schema=schema)
 
    for i in range(0, len(records), batch):
        chunk = records[i:i + batch]
        s_vecs = model.embed_documents([r["statement_text"] for r in chunk])
        m_idx = [j for j, r in enumerate(chunk) if r["method_text"]]
        m_vecs = model.embed_documents([chunk[j]["method_text"] for j in m_idx]) if m_idx else []
        m_map = dict(zip(m_idx, m_vecs))
 
        points = []
        for j, r in enumerate(chunk):
            vec = {"statement": s_vecs[j]}
            if j in m_map:
                vec["method"] = m_map[j]
            points.append(qm.PointStruct(id=abs(hash(r["problem_id"])) % (2**63),
                                         vector=vec, payload=r["payload"]))
        client.upsert(COLLECTION, points=points)
        print(f"  {min(i + batch, len(records))}/{len(records)}")

    docs = []
    for r in records:
        text = r["statement_text"] + ("\n" + r["method_text"] if r["method_text"] else "")
        docs.append(Document(page_content=text, metadata=r["payload"]))
    with (DATA / "bm25_docs.pkl").open("wb") as f:
        pickle.dump(docs, f)
    print("done")    
    

if __name__=='__main__':
    main()