"""Standalone Course Catalog API for Lab 4."""

from fastapi import FastAPI, HTTPException

from data import find_course, get_all_courses
from models import Course


app = FastAPI(title="Course Catalog API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[Course])
def list_courses() -> list[Course]:
    return get_all_courses()


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str) -> Course:
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
