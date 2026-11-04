"""Integration tests on a migrated, seeded PostgreSQL database.
Each test rolls back its changes, including commits made by routes.
"""
import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from db import engine, get_db
from main import app
from try_errors import CASES

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        def override():
            yield self.session
        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()
    def test_filters_pagination_and_validation(self):
        for query, count in [("",6),("?level=beginner",2),("?is_elective=false",4),("?page_size=2&page=2",2)]:
            r=self.client.get('/courses'+query)
            self.assertEqual(r.status_code,200)
            self.assertEqual(len(r.json()),count)
        for query in ('?page=0','?sort=nope','?level=expert','?page_size=101'):
            self.assertEqual(self.client.get('/courses'+query).status_code,422)
        rows=self.client.get('/courses?sort=title').json()
        self.assertEqual([r['title'] for r in rows],sorted(r['title'] for r in rows))
    def test_error_contract_and_session_recovery(self):
        for title,path,body,status in CASES:
            with self.subTest(title=title):
                self.assertEqual(self.client.post(path,json=body).status_code,status)
        self.assertEqual(self.client.get('/courses').status_code,200)
    def test_student_enrollment_join_and_stats(self):
        r=self.client.post('/students',json={'name':'New Student','email':'new@example.com'})
        self.assertEqual(r.status_code,201)
        sid=r.json()['id']
        body={'courseId':'web-security','studentId':sid}
        r=self.client.post('/enrollments',json=body)
        self.assertEqual(r.status_code,201)
        self.assertIn('enrolledAt',r.json())
        rows=self.client.get('/enrollments').json()
        self.assertEqual(rows[-1]['studentName'],'New Student')
        stats=self.client.get('/stats/courses').json()
        self.assertEqual(sum(r['enrolled'] for r in stats),len(rows))
        self.assertEqual(next(r['enrolled'] for r in stats if r['courseId']=='api-design'),0)
    def test_like_and_missing(self):
        before=self.client.get('/courses/api-design').json()['likes']
        for i in (1,2):
            r=self.client.post('/courses/api-design/like')
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()['likes'],before+i)
        for path in ('/courses/nope','/courses/nope/like'):
            r=self.client.post(path) if path.endswith('like') else self.client.get(path)
            self.assertEqual(r.status_code,404)
    def test_docs_cors_and_contract(self):
        self.assertEqual(self.client.get('/docs').status_code,200)
        schema=self.client.get('/openapi.json').json()
        self.assertIn('/stats/courses',schema['paths'])
        r=self.client.options('/enrollments',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.headers['access-control-allow-origin'],'http://localhost:3000')
        self.assertEqual(self.client.post('/enrollments',json={'courseId':'api-design','studentName':'Old contract'}).status_code,422)

if __name__ == '__main__':
    unittest.main()
