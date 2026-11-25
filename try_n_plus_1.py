"""Count SQL queries for nested GraphQL queries."""

import httpx

URL = "http://localhost:8000/graphql"
QUERIES = [
    (
        "students → enrollments → course",
        "{ students { name enrollments { course { title } } } }",
    ),
    (
        "enrollments → course, student",
        "{ enrollments { id course { title } student { name } } }",
    ),
]

for title, query in QUERIES:
    response = httpx.post(URL, json={"query": query})
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    rows = len(next(iter(payload["data"].values())))
    queries = response.headers["x-sql-queries"]
    print(f"{title:<34} rows: {rows:<3} SQL queries: {queries}")
