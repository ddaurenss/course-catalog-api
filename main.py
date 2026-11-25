"""Course Catalog API backed by PostgreSQL (Lab 7)."""
from typing import Annotated, Literal
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from db import get_db
from models import Course, Enrollment, Student
from schemas import CourseOut, CourseStats, EnrollmentDetail, EnrollmentIn, EnrollmentOut, StudentIn, StudentOut
import problem
import services
import counter
from graphql_api import graphql_app

app = FastAPI(title="Course Catalog API")
problem.install(app)
counter.install(app)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])
SessionDep = Annotated[Session, Depends(get_db)]
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}

def pagination(page: Annotated[int, Query(ge=1)] = 1,
               page_size: Annotated[int, Query(ge=1, le=100)] = 20):
    return {"offset": (page - 1) * page_size, "limit": page_size}

@app.get("/courses", response_model=list[CourseOut])
def list_courses(db: SessionDep, p: Annotated[dict, Depends(pagination)],
                 is_elective: bool | None = None,
                 sort: Literal["popular", "title"] = "popular",
                 level: Literal["beginner", "intermediate", "advanced"] | None = None):
    stmt = select(Course)
    if is_elective is not None:
        stmt = stmt.where(Course.is_elective == is_elective)
    if level is not None:
        stmt = stmt.where(Course.level == level)
    order = (Course.title, Course.id) if sort == "title" else (Course.likes.desc(), Course.id)
    return db.scalars(stmt.order_by(*order).offset(p["offset"]).limit(p["limit"])).all()

@app.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: SessionDep):
    course = db.get(Course, course_id)
    if course is None:
        raise services.ServiceError("COURSE_NOT_FOUND", "Course not found")
    return course

@app.post("/courses/{course_id}/like", response_model=CourseOut)
def like_course(course_id: str, db: SessionDep):
    return services.like_course(db, course_id)

@app.post("/students", response_model=StudentOut, status_code=201)
def create_student(data: StudentIn, db: SessionDep):
    return services.create_student(db, data.name, data.email)

@app.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def create_enrollment(data: EnrollmentIn, db: SessionDep):
    return services.enroll(db, data.course_id, data.student_id)

@app.get("/enrollments", response_model=list[EnrollmentDetail])
def list_enrollments(db: SessionDep):
    stmt = select(Enrollment.id, Enrollment.course_id, Course.title.label("course_title"),
                  Enrollment.student_id, Student.name.label("student_name"), Enrollment.enrolled_at)
    return db.execute(stmt.join(Enrollment.course).join(Enrollment.student).order_by(Enrollment.id)).all()

@app.get("/stats/courses", response_model=list[CourseStats])
def course_stats(db: SessionDep):
    enrolled = func.count(Enrollment.id).label("enrolled")
    stmt = select(Course.id.label("course_id"), enrolled).outerjoin(Course.enrollments)
    return db.execute(stmt.group_by(Course.id).order_by(enrolled.desc(), Course.id)).all()
