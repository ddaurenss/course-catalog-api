"""Bonus 5: delete student 3; compare behavior with/without passive_deletes.
Only the dedicated disposable bonus database can be modified.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from db import engine
from models import Enrollment, Student

if engine.url.database != "lab7_bonus_20261112":
    raise SystemExit("Use the disposable lab7_bonus_20261112 database")
with Session(engine) as session:
    student = session.get(Student, 3)
    assert student is not None, "Restore seed before this experiment"
    session.delete(student)
    session.commit()
with Session(engine) as session:
    students = session.scalar(select(func.count()).select_from(Student))
    enrollments = session.scalar(select(func.count()).select_from(Enrollment))
print("students:", students, "enrollments:", enrollments)
assert (students, enrollments) == (2, 5)
engine.dispose()
