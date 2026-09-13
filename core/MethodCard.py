from __future__ import annotations
import re,json,asyncio
from pydantic import BaseModel,Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from collections import Counter
from core.schema import DATA,load_all
import math


METHODS = DATA/"methods.jsonl"

llm=ChatOpenAI(model='openai:gpt-5-mini',temperature=0.2)

METHOD_KEYS = """
dp/linear, dp/prefix-suffix, dp/knapsack, dp/interval, dp/tree-subtree, dp/rerooting,
dp/bitmask, dp/digit, dp/profile, dp/game, dp/probability, dp/cht-convex-hull-trick,
dp/divide-conquer-opt, dp/knuth-opt, dp/matrix-exponentiation, dp/sos-subset-sum,
greedy/exchange-argument, greedy/sort-by-ratio, greedy/heap-scheduling, greedy/sweep,
search/binary-search-answer, search/two-pointers, search/sliding-window,
search/meet-in-the-middle, search/ternary, search/bfs-shortest, search/dijkstra,
search/01-bfs, search/bellman-ford, search/floyd, search/dfs-backtracking,
graph/topological-order, graph/scc-condensation, graph/bridges-articulation,
graph/mst-kruskal, graph/mst-boruvka, graph/bipartite-matching, graph/max-flow,
graph/min-cut-modeling, graph/euler-tour, graph/lca-binary-lifting, graph/hld,
graph/functional-graph-cycles, graph/small-to-large,
ds/union-find, ds/union-find-rollback, ds/fenwick, ds/segment-tree-point,
ds/segment-tree-lazy, ds/segment-tree-descent, ds/merge-sort-tree, ds/sparse-table,
ds/monotonic-stack, ds/monotonic-deque, ds/ordered-set, ds/trie, ds/sqrt-decomposition,
ds/mo-algorithm, ds/persistent,
string/hashing, string/kmp-failure, string/z-function, string/suffix-automaton,
string/aho-corasick, string/manacher, string/suffix-array,
math/modular-inverse, math/combinatorics-nck, math/inclusion-exclusion,
math/mobius-divisor-sieve, math/gcd-number-theory, math/ntt-fft, math/linear-algebra-xor,
math/expected-value-linearity, math/sprague-grundy,
geo/convex-hull, geo/sweep-line, geo/rotating-calipers,
misc/constructive, misc/simulation, misc/bitset-optimization, misc/randomized,
misc/coordinate-compression, misc/offline-queries, misc/prefix-sums-difference-array
"""


class MethodCard(BaseModel):
    method_keys: list[str]=Field(description="1-3 keys from the fixed vocabulary, most important first. "
                    "These are the METHOD, not the topic. A problem that binary "
                    "searches the answer and checks feasibility greedily is "
                    "['search/binary-search-answer', 'greedy/sweep'].", max_length=4)
    steps : list[str]=Field(description="The solution as 3-5 numbered steps. Imperative, "
                                   "concrete, no story nouns. This is what gets embedded.")
    state_signature: str | None = Field(
        default=None,
        description="For DP only: the state and what it means, e.g. "
                    "'dp[i][j] = min cost using first i items with j slots filled'. "
                    "Null for non-DP.")
    transition: str | None = Field(
        default=None, description="For DP only: the recurrence in one line.")
    primitives: list[str] = Field(
        description="Concrete implementation devices actually used in the code: "
                    "'monotonic deque', 'lazy segment tree with range-add range-max', "
                    "'coordinate compression', 'small-to-large merging', 'bitset'.",max_length=6)
    why_it_works: str = Field(description="The correctness argument in 1-2 sentences — "
                                          "exchange argument, monotonicity, optimal substructure.")
    
    complexity : str
    transferable_skill: str = Field(
        description="One sentence: what a solver LEARNS here that transfers to other "
                    "problems. This is the thing we are matching on.")
    
    
PROMPT=ChatPromptTemplate([
    ("system",
     "You are writing the METHOD summary for a competitive programming problem. "
     "You are given the statement, an official editorial when available, and one "
     "or two accepted solutions.\n\n"
     "Rules:\n"
     "1. Describe the SOLUTION PROCEDURE, not the problem. Someone reading your "
     "output should be able to reimplement it without the statement.\n"
     "2. Ground everything in the provided code. If the code uses a Fenwick tree, "
     "say so. Do not describe a textbook approach the code does not use.\n"
     "3. Strip all narrative nouns. 'vertices', 'array elements', 'intervals' — yes. "
     "Character and object names from the story — never.\n"
     "4. method_keys ONLY from this vocabulary:\n{keys}\n"
     "5. If the editorial and the code disagree, trust the code."),
    ("human", "Title: {title}\n\nSTATEMENT:\n{statement}\n\n"
              "EDITORIAL:\n{editorial}\n\nACCEPTED SOLUTION(S):\n{solutions}"),
])

_SIGNALS = {
    "segment_tree":   r"\bseg(ment)?_?tree\b|\bbuild\s*\(|\bupdate\s*\(.*\bnode\b",
    "lazy":           r"\blazy\b|\bpush_?down\b",
    "fenwick":        r"\bbit\s*\[|\bfenwick\b|\btree\s*\[.*\]\s*\+=",
    "dsu":            r"\bfind\s*\(\s*\w+\s*\)|\bunion\s*\(|\bparent\s*\[|\bdsu\b",
    "priority_queue": r"priority_queue|heapq|PriorityQueue",
    "ordered_set":    r"\bset<|\bmap<|TreeMap|TreeSet|SortedList",
    "deque":          r"\bdeque\b|collections\.deque|ArrayDeque",
    "bitmask":        r"1\s*<<\s*\w+|__builtin_popcount|bit_count\(",
    "modular":        r"1e9\s*\+\s*7|998244353|1000000007",
    "recursion":      r"\b(dfs|solve|rec)\s*\([^)]*\)\s*\{[^}]*\b\1\s*\(",
    "sorting":        r"\bsort\s*\(|\.sort\(|sorted\(",
    "binary_search":  r"lower_bound|upper_bound|bisect_|while\s*\(\s*lo\s*[<+]",
    "two_pointers":   r"while\s*\(\s*\w+\s*<\s*\w+\s*\).*\+\+|\bl\+\+.*\br\+\+",
    "dp_table":       r"\bdp\s*\[|\bmemo\b|@lru_cache|@cache",
    "graph_adj":      r"\badj\s*\[|\bg\s*\[\w+\]\.push_back|graph\s*\[",
    "gcd":            r"__gcd|\bgcd\s*\(|math\.gcd",
    "string_hash":    r"\bhash\b.*\bbase\b|\bpw\s*\[",
}

_LOOP=re.compile(r"\bfor\s*[\(:]|\bwhile\s*\(")

def fingerprint(code: str) -> dict:
    #detecting tokens from the provided code that is the loops or other keywords
    fp = {k: bool(re.search(p, code, re.I | re.S)) for k, p in _SIGNALS.items()}
    fp["loop_count"] = len(_LOOP.findall(code))
    fp["lines"] = code.count("\n") + 1
    return fp


_LOOP_BUCKETS = (("loops_1", 0, 1), ("loops_2_3", 2, 3), ("loops_4_6", 4, 6),
                 ("loops_7p", 7, 10 ** 9))

def fp_components(fp:dict)->list[str]:
    out=[k for k in fp if fp.get(k)]
    n=fp.get('loop_count',0)
    out+=[name for name,lo,hi in _LOOP_BUCKETS if lo<=n<=hi]
    return out
    

#creating the vectors out of the matched signals


def fp_idf(fingerprints,smoothing=1.0)->dict[str,float]:
    fps=list(fingerprints)
    n=len(fps) or 1
    df = Counter(c for fp in fps for c in set(fp_components(fp)))
    names = list(_SIGNALS) + [b[0] for b in _LOOP_BUCKETS]
    return {k: math.log((n + smoothing) / (df.get(k, 0) + smoothing)) + 1.0
            for k in names}
    

#calculating the cosine similarity
def fp_similarity(a: dict, b: dict, idf: dict[str, float] | None = None) -> float:

    ca, cb = fp_components(a), fp_components(b)
    if not ca or not cb:
        return 0.0
    w = (lambda k: idf.get(k, 1.0)) if idf else (lambda k: 1.0)
    sb = {k: w(k) for k in cb}
    dot = sum(w(k) * sb[k] for k in ca if k in sb)
    na = math.sqrt(sum(w(k) ** 2 for k in ca))
    nb = math.sqrt(sum(v ** 2 for v in sb.values()))
    return dot / (na * nb) if na and nb else 0.0



def method_to_text(title: str, platform: str, m: dict) -> str:

    parts = [
        f"Method: {', '.join(m['method_keys'])}.",
        f"Steps: {m['steps']}",
    ]
    if m.get("state_signature"):
        parts.append(f"DP state: {m['state_signature']}")
    if m.get("transition"):
        parts.append(f"Transition: {m['transition']}")
    parts += [
        f"Implementation: {', '.join(m.get('primitives') or []) or 'none'}.",
        f"Correctness: {m['why_it_works']}",
        f"Complexity: {m['complexity']}.",
        f"Transferable skill: {m['transferable_skill']}",
        f"({title}, {platform})",
    ]
    return "\n".join(parts)


async def _one(chain, sem, p, sol):
    async with sem:
        try:
            card = await chain.ainvoke({
                "keys": METHOD_KEYS,
                "title": p["title"],
                "statement": p["statement"][:4000],
                "editorial": (sol.get("editorial") or "none")[:4000],
                "solutions": "\n\n---\n\n".join(sol["solutions"])[:8000],
            })
            code = "\n".join(sol["solutions"])
            return {"problem_id": p["problem_id"], 
                    "method": card.model_dump(),
                    "fingerprint": fingerprint(code),
                    "sol_source": sol["source"]}
        except Exception as e:
            print(f"fail {p['problem_id']}: {e}")
            return None

async def process(concurrency : int=12):
    from core.schema import laod_all
    from Ingestion.Get_Solutions import SOLUTIONS
    
    problems={p['problem_id'] : p for p in load_all}
    
    sols={}
    with SOLUTIONS.open(encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    sols.setdefault(r["problem_id"], r)
 
    done=set()
    if METHODS.exists:
        with METHODS.open(encoding='utf-8') as f :
            done=[json.loads(l)['problem_id'] for l in f if l.strip()]
            
    
    todos=[]
    todo = [(problems[pid], s) for pid, s in sols.items() if pid in problems and pid not in done]

    chain=PROMPT | llm.with_structured_output(MethodCard)
    sem=asyncio.Semaphore(concurrency)
    with METHODS.open("a", encoding="utf-8") as out:
        for i in range(0, len(todo), 200):
            batch = todo[i:i + 200]
            for r in await asyncio.gather(*[_one(chain, sem, p, s) for p, s in batch]):
                if r:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            print(f"methods {min(i + 200, len(todo))}/{len(todo)}")
    
    
if __name__=="__main__":
    process()