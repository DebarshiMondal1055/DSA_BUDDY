"""LeetCode via the public GraphQL endpoint. Premium problems return null content."""
from __future__ import annotations
import time, json, requests
from bs4 import BeautifulSoup
from core.schema import Problem, DATA, clean_text, normalize_difficulty, write_jsonl

GQL = "https://leetcode.com/graphql"
HEAD = {
    "User-Agent": "Mozilla/5.0 (compatible; dsa-similarity-research/0.1)",
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/problemset/all/",
}

LIST_Q = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
    total: totalNum
    questions: data { frontendQuestionId: questionFrontendId title titleSlug difficulty
                      paidOnly: isPaidOnly topicTags { name slug } }
  }
}"""

DETAIL_Q = """
query questionContent($titleSlug: String!) {
  question(titleSlug: $titleSlug) { content }
}"""

CACHE = DATA / "html" / "lc"
CACHE.mkdir(parents=True, exist_ok=True)


def gql(query: str, variables: dict) -> dict:
    r = requests.post(GQL, headers=HEAD,
                      data=json.dumps({"query": query, "variables": variables}), timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def fetch_index() -> list[dict]:
    out, skip, page = [], 0, 100
    while True:
        d = gql(LIST_Q, {"categorySlug": "", "limit": page, "skip": skip, "filters": {}})
        block = d["problemsetQuestionList"]
        out += block["questions"]
        skip += page
        if skip >= block["total"]:
            break
        time.sleep(0.6)
    return out


def fetch_statement(slug: str) -> str | None:
    key = CACHE / f"{slug}.html"
    if key.exists():
        html = key.read_text(encoding="utf-8")
    else:
        content = gql(DETAIL_Q, {"titleSlug": slug})["question"]["content"]
        if not content:
            return None
        html = content
        key.write_text(html, encoding="utf-8")
        time.sleep(0.8)
    soup = BeautifulSoup(html, "lxml")
    for junk in soup.select("pre"):        # example IO blocks
        junk.decompose()
    return clean_text(soup.get_text("\n"))


def main(limit: int | None = None):
    out = []
    for i, q in enumerate(fetch_index()):
        if limit and i >= limit:
            break
        if q["paidOnly"]:
            continue
        stmt = fetch_statement(q["titleSlug"])
        if not stmt or len(stmt) < 80:
            continue
        out.append(Problem(
            problem_id=f"lc:{q['frontendQuestionId']}",
            platform="leetcode",
            title=q["title"],
            url=f"https://leetcode.com/problems/{q['titleSlug']}/",
            statement=stmt,
            tags=[t["name"] for t in q.get("topicTags", [])],
            difficulty=normalize_difficulty("leetcode", q["difficulty"]),
            raw_difficulty=q["difficulty"],
        ))
        if len(out) % 200 == 0:
            print(f"leetcode: {len(out)}")
    write_jsonl(DATA / "leetcode.jsonl", out)
    print(f"leetcode: wrote {len(out)}")


if __name__ == "__main__":
    main()
