SELECT
    (SELECT count(*) FROM courses) AS courses,
    (SELECT count(*) FROM students) AS students,
    (SELECT count(*) FROM enrollments) AS enrollments;