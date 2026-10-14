"""Acceptance checks: run with python -m unittest -v."""

import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from data import get_all_courses
from main import app
from models import Course


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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
            "credits": 4, "is_elective": False, "likes": 21,
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
        self.assertEqual(set(schema["paths"]), {"/", "/courses", "/courses/{course_id}"})
        self.assertTrue(all(set(methods) == {"get"} for methods in schema["paths"].values()))
        fields = schema["components"]["schemas"]["Course"]["properties"]
        self.assertEqual(set(fields), {"id", "title", "description", "credits", "is_elective", "likes"})
        self.assertEqual(fields["is_elective"]["default"], False)
        self.assertEqual(fields["likes"]["default"], 0)
        params = schema["paths"]["/courses"]["get"]["parameters"]
        self.assertEqual({p["name"] for p in params}, {"is_elective", "sort", "page", "page_size"})


if __name__ == "__main__":
    unittest.main()
