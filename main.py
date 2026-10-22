"""Standalone Course Catalog API for Labs 4–5."""

from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query

from data import find_course, get_all_courses
from models import Course, Enrollment, EnrollmentIn
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Course Catalog API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENROLLMENTS: list[Enrollment] = []


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Course Catalog API is running"}


def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, int]:
    return {"offset": (page - 1) * page_size, "limit": page_size}


@app.get("/courses", response_model=list[Course])
def list_courses(
    p: Annotated[dict[str, int], Depends(pagination)],
    is_elective: bool | None = None,
    sort: Literal["popular", "title"] = "popular",
) -> list[Course]:
    courses = get_all_courses()
    if is_elective is not None:
        courses = [course for course in courses if course.is_elective == is_elective]
    if sort == "title":
        courses = sorted(courses, key=lambda course: course.title)
    else:
        courses = sorted(courses, key=lambda course: course.likes, reverse=True)
    return courses[p["offset"] : p["offset"] + p["limit"]]


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str) -> Course:
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/courses/{course_id}/like", response_model=Course)
def like_course(course_id: str) -> Course:
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.likes += 1
    return course


@app.post("/enrollments", response_model=Enrollment, status_code=201)
def create_enrollment(data: EnrollmentIn) -> Enrollment:
    if find_course(data.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    enrollment = Enrollment(id=len(ENROLLMENTS) + 1, **data.model_dump())
    ENROLLMENTS.append(enrollment)
    return enrollment


@app.get("/enrollments", response_model=list[Enrollment])
def list_enrollments() -> list[Enrollment]:
    return ENROLLMENTS
