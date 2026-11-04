"""Run from the API root against the dedicated disposable PostgreSQL database."""
import os, subprocess, sys
from pathlib import Path
import psycopg
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert u.database=='lab7_verify_20261105'
c=psycopg.connect(host=u.host,port=u.port,user=u.username,password=u.password,dbname=u.database,autocommit=True)
def sql(s):
 print('SQL:',s,flush=True)
 with c.cursor() as q:
  q.execute(s)
  if q.description: print(q.fetchall(),flush=True)
def run(*args,ok=True):
 print('$',' '.join(args),flush=True)
 r=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(r.stdout,flush=True)
 assert (r.returncode==0)==ok,(args,r.returncode)
 return r.stdout
def a(*args,**kw):return run(sys.executable,'-m','alembic',*args,**kw)
def patch(path,old,new,action):
 p=Path(path);s=p.read_text();assert old in s
 try:p.write_text(s.replace(old,new));action()
 finally:p.write_text(s)
# Recreate the disposable public schema so this runner is repeatable.
sql('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
sql(Path('../course-catalog-db/schema.sql').read_text())
sql(Path('../course-catalog-db/seed.sql').read_text())
a('upgrade','0001',ok=False);a('stamp','0001')
print('EXPERIMENT 5: NOT NULL without backfill',flush=True)
patch('alembic/versions/0002_add_course_level.py','nullable=True','nullable=False',lambda:a('upgrade','head',ok=False))
sql('SELECT version_num FROM alembic_version')
a('upgrade','head');a('check')
print('EXPERIMENT 1: incorrect uq convention',flush=True)
patch('db.py','%(column_0_N_name)s_key','%(column_0_N_name)s_uniq',lambda:run(sys.executable,'check_models.py',ok=False))
print('EXPERIMENT 2: no minimum name validation',flush=True)
code="""from fastapi.testclient import TestClient
from main import app
r=TestClient(app,raise_server_exceptions=False).post('/students',json={'name':'N','email':'n@example.com'})
print(r.status_code,r.text)
assert r.status_code==500
from sqlalchemy import text
from db import engine
from sqlalchemy.exc import IntegrityError
try:
 with engine.begin() as c:c.execute(text("INSERT INTO students(name,email) VALUES ('N','n@example.com')"))
except IntegrityError as e:print(type(e.orig).__name__,e.orig.diag.constraint_name)
"""
patch('schemas.py','name: str = Field(min_length=2)','name: str',lambda:run(sys.executable,'-c',code))
print('EXPERIMENT 3: wrong constraint mapping',flush=True)
code="""from fastapi.testclient import TestClient
from main import app
r=TestClient(app,raise_server_exceptions=False).post('/students',json={'name':'Aigerim Two','email':'aigerim@example.com'})
print(r.status_code,r.text)
assert r.status_code==500
"""
patch('main.py','"students_email_key":','"students_email_uniq":',lambda:run(sys.executable,'-c',code))
print('EXPERIMENT 4: nullability and type drift',flush=True)
sql('ALTER TABLE courses ALTER COLUMN title DROP NOT NULL')
try:a('check',ok=False)
finally:sql('ALTER TABLE courses ALTER COLUMN title SET NOT NULL')
sql('ALTER TABLE courses ALTER COLUMN title TYPE varchar(100)')
try:a('check',ok=False)
finally:sql('ALTER TABLE courses ALTER COLUMN title TYPE text')
print('UPGRADE / DOWNGRADE / UPGRADE',flush=True)
a('downgrade','-1')
try:sql('SELECT level FROM courses')
except psycopg.errors.UndefinedColumn as e:print(type(e).__name__,str(e),flush=True)
a('upgrade','head');sql('SELECT id,level FROM courses ORDER BY id')
print('EXPERIMENT 6: missing import models',flush=True)
try:
 patch('alembic/env.py','import models  #','# import models  #',lambda:a('revision','--autogenerate','-m','oops','--rev-id','0003'))
 f=next(Path('alembic/versions').glob('0003_*.py'));s=f.read_text();print(s,flush=True);assert 'op.drop_table(' in s
finally:
 for f in Path('alembic/versions').glob('0003_*.py'):f.unlink()
print('EXPERIMENT 7: no migration for phone',flush=True)
patch('models.py','    email: Mapped[str] = mapped_column(unique=True)','    email: Mapped[str] = mapped_column(unique=True)\n    phone: Mapped[str | None]',lambda:a('check',ok=False))
print('EXPERIMENT 8: two heads and merge',flush=True)
try:
 a('revision','-m','add student phone','--rev-id','0003')
 a('revision','-m','add course language','--rev-id','0004','--head','0002','--splice')
 a('heads');a('upgrade','head',ok=False)
 a('merge','heads','-m','merge phone and language','--rev-id','0005')
 a('heads');a('history')
finally:
 for rev in ('0003','0004','0005'):
  for f in Path('alembic/versions').glob(rev+'_*.py'):f.unlink()
a('heads');a('check')
print('CLEAN START on disposable database',flush=True)
a('downgrade','base');a('upgrade','head');sql(Path('seed.sql').read_text());a('check')
run(sys.executable,'check_db.py');run(sys.executable,'check_models.py');run(sys.executable,'-m','unittest','-v')
a('upgrade','0001:0002','--sql');c.close()
print('ALL EIGHT EXPERIMENTS AND CLEAN START PASSED',flush=True)
