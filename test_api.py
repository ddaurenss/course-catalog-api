"""Acceptance checks: run with python -m unittest -v."""

import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from data import get_all_courses
from main import app, ENROLLMENTS
from models import Course


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        ENROLLMENTS.clear()
        for course in get_all_courses():
            if course.id == "web-security":
                course.likes = 21

    def test_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Course Catalog API is running"})

    def test_list_filter_sort_and_pages(self):
        cases = {
            "/courses": ["ai-integration", "modern-frontend", "web-security", "backend-fastapi", "databases-postgresql", "api-design"],
            "/courses?is_elective=true": ["ai-integration", "api-design"],
            "/courses?is_elective=false": ["modern-frontend", "web-security", "backend-fastapi", "databases-postgresql"],
            "/courses?sort=title": ["ai-integration", "api-design", "backend-fastapi", "modern-frontend", "databases-postgresql", "web-security"],
            "/courses?page=1&page_size=2": ["ai-integration", "modern-frontend"],
            "/courses?page=2&page_size=2": ["web-security", "backend-fastapi"],
            "/courses?page=3&page_size=2": ["databases-postgresql", "api-design"],
            "/courses?page=4&page_size=2": [],
            "/courses?is_elective=false&sort=title&page=2&page_size=2": ["databases-postgresql", "web-security"],
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([course["id"] for course in response.json()], expected)

    def test_single_course_and_missing_course(self):
        response = self.client.get("/courses/web-security")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "id": "web-security", "title": "Web Security Essentials",
            "description": "JWT/OAuth2, XSS, CSRF, and SQL injection defense.",
            "credits": 4, "isElective": False, "likes": 21,
        })
        response = self.client.get("/courses/nope")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Course not found"})

    def test_invalid_queries(self):
        for query in ("sort=banana", "page=0", "page=-1", "page_size=0", "page_size=1000", "page=abc", "is_elective=banana"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"/courses?{query}").status_code, 422)

    def test_model_validation_and_defaults(self):
        course = Course(id="x", title="t", description="d", credits="5")
        self.assertEqual(course.credits, 5)
        self.assertFalse(course.is_elective)
        self.assertEqual(course.likes, 0)
        with self.assertRaises(ValidationError):
            Course(id="x", title="t", description="d", credits="five")

    def test_queries_do_not_reorder_source(self):
        original = [course.id for course in get_all_courses()]
        self.client.get("/courses?sort=title")
        self.client.get("/courses?is_elective=true")
        self.assertEqual([course.id for course in get_all_courses()], original)
        copy = get_all_courses()
        copy.clear()
        self.assertEqual(len(get_all_courses()), 6)

    def test_documentation_and_schema(self):
        for path in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(set(schema["paths"]), {"/", "/courses", "/courses/{course_id}", "/courses/{course_id}/like", "/enrollments"})
        self.assertEqual(set(schema["paths"]["/enrollments"]), {"get", "post"})
        fields = schema["components"]["schemas"]["Course"]["properties"]
        self.assertEqual(set(fields), {"id", "title", "description", "credits", "isElective", "likes"})
        self.assertEqual(fields["isElective"]["default"], False)
        self.assertEqual(fields["likes"]["default"], 0)
        params = schema["paths"]["/courses"]["get"]["parameters"]
        self.assertEqual({p["name"] for p in params}, {"is_elective", "sort", "page", "page_size"})

    def test_cors_and_preflight(self):
        for origin, allowed in [("http://localhost:3000", True), ("http://evil.example", False)]:
            response = self.client.get("/courses", headers={"Origin": origin})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("access-control-allow-origin"), origin if allowed else None)
            response = self.client.options("/enrollments", headers={"Origin": origin,
                "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
            self.assertEqual(response.status_code, 200 if allowed else 400)

    def test_writes_and_validation(self):
        for likes in (22, 23):
            response = self.client.post("/courses/web-security/like")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["likes"], likes)
        self.assertEqual(self.client.get("/courses/web-security").json()["likes"], 23)
        self.assertEqual(self.client.post("/courses/nope/like").status_code, 404)
        body = {"courseId": "web-security", "studentName": "Aigerim"}
        response = self.client.post("/enrollments", json=body)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {**body, "id": 1})
        self.assertEqual(self.client.get("/enrollments").json(), [response.json()])
        invalid = self.client.post("/enrollments", json={**body, "studentName": "A"})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["detail"][0]["loc"], ["body", "studentName"])
        self.assertEqual(self.client.post("/enrollments", json={**body, "courseId": "nope"}).status_code, 404)
        self.assertEqual(len(self.client.get("/courses?isElective=true").json()), 6)


if __name__ == "__main__":
    unittest.main()
