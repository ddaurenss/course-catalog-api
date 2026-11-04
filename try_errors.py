"""Run against a seeded running API: python try_errors.py."""
import os
import httpx
CASES = [
    ("email already taken", "/students", {"name": "Aigerim Two", "email": "aigerim@example.com"}, 409),
    ("already enrolled", "/enrollments", {"courseId": "ai-integration", "studentId": 3}, 409),
    ("unknown course", "/enrollments", {"courseId": "nope", "studentId": 3}, 404),
    ("unknown student", "/enrollments", {"courseId": "web-security", "studentId": 999}, 404),
    ("name too short", "/students", {"name": "N", "email": "n@example.com"}, 422),
]
if __name__ == "__main__":
    with httpx.Client(base_url=os.getenv("API_URL", "http://localhost:8000")) as client:
        results = []
        for title, path, body, expected in CASES:
            r = client.post(path, json=body)
            results.append(r.status_code == expected)
            print(title, r.status_code, r.text)
    print(f"{sum(results)} of {len(results)} as expected")
    raise SystemExit(not all(results))
