-- Expected errors in first scenario; run on seeded course_catalog.
\set ON_ERROR_STOP off
\set VERBOSITY verbose
BEGIN;
INSERT INTO students (name,email) VALUES ('Madina Ospanova','madina@example.com');
INSERT INTO enrollments (course_id,student_id)
SELECT 'no-such-course',id FROM students WHERE email = 'madina@example.com';
SELECT count(*) FROM students; -- expected 25P02: transaction aborted
ROLLBACK;
SELECT count(*) AS after_rollback FROM students WHERE email = 'madina@example.com';
\set ON_ERROR_STOP on
\set VERBOSITY default
-- The successful two-session experiment is described in README.md.
