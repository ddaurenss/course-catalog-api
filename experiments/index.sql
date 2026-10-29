-- Connect to idx_demo; recreates only that disposable database's tables.
\set ON_ERROR_STOP on
SELECT current_database() = 'idx_demo' AS correct_database \gset
\if :correct_database
\ir ../schema.sql
DROP INDEX enrollments_student_id_idx;
\ir idx_data.sql
EXPLAIN SELECT * FROM students WHERE email = 'student777@example.com';
EXPLAIN SELECT * FROM enrollments WHERE course_id = 'course-7';
EXPLAIN SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
CREATE INDEX enrollments_student_id_idx ON enrollments(student_id);
EXPLAIN SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
SELECT pg_size_pretty(pg_relation_size('enrollments')) AS table_size,
pg_size_pretty(pg_relation_size('enrollments_student_id_idx')) AS index_size;
\else
\echo 'Connect to idx_demo to run this experiment.'
\quit 1
\endif
