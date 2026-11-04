from sqlalchemy import select, text
from db import Base, SessionLocal
from models import Course, Student, Enrollment
with SessionLocal() as db:
    for model in (Course, Student, Enrollment):
        print(f"{model.__tablename__}: {len(db.scalars(select(model)).all())} rows")
    names = set(db.scalars(text("""SELECT conname FROM pg_constraint
    WHERE connamespace = 'public'::regnamespace AND contype IN ('p','u','f','c')
    UNION SELECT indexname FROM pg_indexes WHERE schemaname = 'public'""")))
    names = {n for n in names if not n.startswith('alembic')}
expected = {c.name for t in Base.metadata.tables.values() for c in [*t.constraints, *t.indexes]}
print("names only in models:", sorted(expected - names) or "none")
print("names only in database:", sorted(names - expected) or "none")
assert names == expected
