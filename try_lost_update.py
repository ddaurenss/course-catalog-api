"""Bonus 4: compare two read/modify/write updates with SQL expressions.
Run only on the dedicated bonus database. Reset seed between variants.
"""
import argparse
from sqlalchemy.orm import Session
from db import engine
from models import Course

parser = argparse.ArgumentParser()
parser.add_argument("--atomic", action="store_true")
args = parser.parse_args()
if engine.url.database != "lab7_bonus_20261112":
    raise SystemExit("Use the disposable lab7_bonus_20261112 database")
with Session(engine) as alice, Session(engine) as bob:
    a = alice.get(Course, "api-design")
    b = bob.get(Course, "api-design")
    initial = a.likes
    assert initial == 11 and b.likes == 11, "Restore seed before each variant"
    print("Alice reads", a.likes, "| Bob reads", b.likes)
    a.likes = Course.likes + 1 if args.atomic else a.likes + 1
    alice.commit()
    b.likes = Course.likes + 1 if args.atomic else b.likes + 1
    bob.commit()
with Session(engine) as session:
    actual = session.get(Course, "api-design").likes
print("mode:", "atomic SQL expression" if args.atomic else "read/modify/write")
print("in the database:", actual)
assert actual == (13 if args.atomic else 12)
engine.dispose()
