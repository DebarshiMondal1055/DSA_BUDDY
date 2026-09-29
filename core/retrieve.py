from __future__ import annotations
import pickle, re, requests
from collections import defaultdict
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_classic.retrievers import BM25Retriever
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import CrossEncoder
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from core.schema import DATA, clean_text
from core.embedindex import COLLECTION, QDRANT_URL, get_embeddings
from core.Distillation import build_chain as build_concept_chain, VOCAB, card_to_text
from core.MethodCard import (MethodCard, METHOD_KEYS, PROMPT as METHOD_PROMPT,
                         method_to_text, fingerprint, fp_similarity)

PLATFORMS = ("codeforces", "leetcode", "atcoder")
_rr = None


def reranker():
    global _rr
    if _rr is None:
        _rr = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=768)
    return _rr


class SimilarProblemSearch:
    def __init__(self, model: str = "openai:gpt-5-mini"):
        self.emb = get_embeddings()
        self.client = QdrantClient(url=QDRANT_URL, timeout=60)
        self.concept_chain = build_concept_chain(model)
        llm = init_chat_model(model, temperature=0)
        self.method_chain = METHOD_PROMPT | llm.with_structured_output(MethodCard)
        self.llm = llm
        with (DATA / "bm25_docs.pkl").open("rb") as f:
            self.bm25 = BM25Retriever.from_documents(pickle.load(f), k=60)

    # ------------------------------------------------------------ input
    def resolve(self, query: str) -> dict:
        if query.strip().startswith("http"):
            return self._fetch_url(query.strip())
        return {"title": "(pasted)", "statement": query, "platform": None, "tags": []}

    def _fetch_url(self, url: str) -> dict:
        h = {"User-Agent": "Mozilla/5.0 (compatible; dsa-similarity/0.1)"}
        if "leetcode.com" in url:
            from Ingestion.leetcode import fetch_statement
            slug = re.search(r"/problems/([^/]+)", url).group(1)
            return {"title": slug.replace("-", " "), "statement": fetch_statement(slug),
                    "platform": "leetcode", "tags": []}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=30).text, "lxml")
        if "codeforces.com" in url:
            node, plat = soup.select_one("div.problem-statement"), "codeforces"
        elif "atcoder.jp" in url:
            node = soup.select_one("span.lang-en") or soup.select_one("#task-statement")
            plat = "atcoder"
        else:
            node, plat = soup.body, None
        return {"title": (soup.title.string if soup.title else "")[:120],
                "statement": clean_text(node.get_text("\n")) if node else "",
                "platform": plat, "tags": []}

    # ------------------------------------------------------------ query cards
    def _build_query(self, src: dict, solution_code: str | None):
        concept = self.concept_chain.invoke({
            "vocab": VOCAB, "title": src["title"], "difficulty": None,
            "tags": ", ".join(src["tags"]) or "none",
            "statement": src["statement"][:6000],
        }).model_dump()

        # If the user pasted their AC code, the method comes from the code — far
        # more reliable than inferring it. Otherwise derive the intended method
        # from the statement and flag it as inferred.
        method = self.method_chain.invoke({
            "keys": METHOD_KEYS, "title": src["title"],
            "statement": src["statement"][:4000], "editorial": "none",
            "solutions": solution_code[:8000] if solution_code
                         else "(not provided — infer the intended solution "
                              "from the statement and constraints)",
        }).model_dump()

        return concept, method, (fingerprint(solution_code) if solution_code else None)

    # ------------------------------------------------------------ search
    def _dense(self, text: str, view: str, k: int, flt):
        vec = self.emb.embed_query(text)
        hits = self.client.query_points(
            COLLECTION, query=vec, using=view, limit=k,
            query_filter=flt, with_payload=True).points
        return [Document(page_content=h.payload.get("steps") or h.payload["reduction"],
                         metadata=h.payload) for h in hits]

    def search(self, query  : str, k: int = 12, mode: str = "both",
               solution_code: str | None = None, exclude_same_platform: bool = True,
               per_platform_min:int=3,difficulty_window: int | None = None):
        src = self.resolve(query)
        concept, method, fp = self._build_query(src, solution_code)
        c_text = card_to_text(src["title"], src["platform"] or "unknown", concept)
        m_text = method_to_text(src["title"], src["platform"] or "unknown", method)

        must = []
        if difficulty_window and src.get("difficulty") is not None:
            lo = src["difficulty"] - difficulty_window
            hi = src["difficulty"] + difficulty_window
            must.append(qm.FieldCondition(key="difficulty",
                                          range=qm.Range(gte=lo, lte=hi)))
        flt = qm.Filter(must=must) if must else None

        lists, weights = [], []
        if mode in ("both", "concept"):
            lists.append(self._dense(c_text, "statement", 90, flt)); weights.append(0.45)
        if mode in ("both", "method"):
            m_flt = qm.Filter(must=(must or []) + [qm.FieldCondition(
                key="has_method", match=qm.MatchValue(value=True))])
            lists.append(self._dense(m_text, "method", 90, m_flt)); weights.append(0.55)
        lists.append(self.bm25.invoke(m_text if mode == "method" else c_text))
        weights.append(0.15)

        fused = self._rrf(lists, weights)

        # Exact method-key agreement is a strong, cheap signal — promote it.
        qkeys = set(method["method_keys"])
        qprims = set(p.lower() for p in method.get("primitives") or [])
        for d in fused:
            md = d.metadata
            bonus = 0.0
            shared = qkeys & set(md.get("method_keys") or [])
            if shared:
                bonus += 0.30 * len(shared) / max(len(qkeys), 1)
                if md.get("method_keys") and md["method_keys"][0] in qkeys:
                    bonus += 0.10                       # same PRIMARY method
            prims = set(p.lower() for p in md.get("primitives") or [])
            if qprims and prims:
                bonus += 0.15 * len(qprims & prims) / len(qprims | prims)
            if fp and md.get("fingerprint"):
                bonus += 0.10 * fp_similarity(fp, md["fingerprint"])
            md["_bonus"] = bonus

        pairs = [(m_text if mode != "concept" else c_text, d.page_content)
                 for d in fused[:120]]
        ce = reranker().predict(pairs) if pairs else []
        scored = sorted(zip(ce, fused[:120]),
                        key=lambda x: -(float(x[0]) + x[1].metadata["_bonus"]))
        ranked = [d for _, d in scored
                  if d.metadata["problem_id"] != src.get("problem_id")]

        picked = self._cover_platforms(ranked, k, per_platform_min)
        return {
            "source": {"title": src["title"], "platform": src["platform"],
                       "concept": concept, "method": method,
                       "method_from": "your code" if solution_code else "inferred"},
            "results": self._explain(method, concept, picked, mode),
        }

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _rrf(lists, weights, c: int = 60):
        score, seen = defaultdict(float), {}
        for lst, w in zip(lists, weights):
            for rank, d in enumerate(lst):
                pid = d.metadata["problem_id"]
                score[pid] += w / (c + rank + 1)
                seen[pid] = d
        return [seen[p] for p, _ in sorted(score.items(), key=lambda x: -x[1])]

    @staticmethod
    def _cover_platforms(ranked, k, per_platform_min):
        """Guarantee each platform appears. Fill quotas first, then best-overall,
        capping near-duplicate methods so you don't get 12 flavours of one trick."""
        out, used = [], set()
        by_plat = {p: [d for d in ranked if d.metadata["platform"] == p]
                   for p in PLATFORMS}
        for p in PLATFORMS:
            for d in by_plat[p][:per_platform_min]:
                out.append(d); used.add(d.metadata["problem_id"])
        by_key = defaultdict(int)
        for d in out:
            by_key[tuple(d.metadata.get("method_keys") or [])] += 1
        for d in ranked:
            if len(out) >= k:
                break
            pid = d.metadata["problem_id"]
            key = tuple(d.metadata.get("method_keys") or [])
            if pid in used or by_key[key] >= 3:
                continue
            out.append(d); used.add(pid); by_key[key] += 1
        return out[:k]

    def _explain(self, qmethod, qconcept, docs, mode):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You compare two competitive programming problems for a "
                       "solver deciding what to practise next. In ONE sentence say "
                       "what solution machinery they share (be specific: name the "
                       "DP state shape, the data structure, the argument). Then one "
                       "clause on what the candidate adds or changes. No preamble."),
            ("human", "SOURCE METHOD:\n{q}\n\nCANDIDATE:\n{c}"),
        ])
        q = (f"{', '.join(qmethod['method_keys'])} | {qmethod['steps']} | "
             f"state={qmethod.get('state_signature')} | "
             f"primitives={', '.join(qmethod.get('primitives') or [])}")
        msgs = (prompt | self.llm).batch(
            [{"q": q, "c": (d.metadata.get("steps") or d.metadata["reduction"])
              + f"\nmethod={d.metadata.get('method_keys')}"} for d in docs])
        out = []
        for d, msg in zip(docs, msgs):
            m = d.metadata
            out.append({
                "problem_id": m["problem_id"], "title": m["title"],
                "platform": m["platform"], "url": m["url"],
                "difficulty": m["difficulty"],
                "method_keys": m.get("method_keys") or [],
                "concept_tags": m.get("concept_tags") or [],
                "primitives": m.get("primitives") or [],
                "state_signature": m.get("state_signature"),
                "shared_method_keys": sorted(set(qmethod["method_keys"])
                                             & set(m.get("method_keys") or [])),
                "why": msg.content.strip(),
            })
        return out

    # ------------------------------------------------------------ drill ladder
    def ladder(self, method_key: str, around: int | None = None, n: int = 12):
        """Practice mode: every problem using this exact method, easiest first,
        spread across platforms. Pure metadata query, no LLM, instant."""
        must = [qm.FieldCondition(key="method_keys",
                                  match=qm.MatchValue(value=method_key))]
        if around is not None:
            must.append(qm.FieldCondition(
                key="difficulty", range=qm.Range(gte=around - 20, lte=around + 20)))
        pts, _ = self.client.scroll(COLLECTION, scroll_filter=qm.Filter(must=must),
                                    limit=400, with_payload=True)
        rows = sorted((p.payload for p in pts), key=lambda r: r["difficulty"])
        out, per = [], defaultdict(int)
        for r in rows:
            if per[r["platform"]] >= n // 3 + 1:
                continue
            out.append({k: r[k] for k in ("problem_id", "title", "platform",
                                          "url", "difficulty", "method_keys")})
            per[r["platform"]] += 1
            if len(out) >= n:
                break
        return sorted(out, key=lambda r: r["difficulty"])
