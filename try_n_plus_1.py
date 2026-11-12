"""Bonus 3: count lazy loading and selectinload queries on seeded data."""
from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload
from db import engine
from models import Course

with engine.connect():
    pass
queries = []
def count_query(conn, cursor, statement, parameters, context, executemany):
    queries.append(statement)
event.listen(engine, "before_cursor_execute", count_query)
try:
    for name, options in [("lazy", []), ("selectinload", [selectinload(Course.enrollments)])]:
        queries.clear()
        with Session(engine) as session:
            courses = session.scalars(select(Course).options(*options)).all()
            total = sum(len(course.enrollments) for course in courses)
        print(f"{name:13} enrollments: {total}, queries: {len(queries)}")
        assert total == 6
        assert len(queries) == (7 if name == "lazy" else 2)
finally:
    event.remove(engine, "before_cursor_execute", count_query)
    engine.dispose()
