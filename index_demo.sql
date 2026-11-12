-- 1. Подготовка: временно убрать отдельный индекс
BEGIN;

DROP INDEX IF EXISTS public.enrollments_student_id_idx;

ANALYZE enrollments;


-- 2. ДО индекса: выполнить этот запрос три раза
EXPLAIN ANALYZE
SELECT *
FROM enrollments
WHERE student_id = 777;


-- 3. Создать индекс
CREATE INDEX enrollments_student_id_idx
ON enrollments(student_id);


-- 4. ПОСЛЕ индекса: выполнить этот запрос три раза
EXPLAIN ANALYZE
SELECT *
FROM enrollments
WHERE student_id = 777;


-- 5. Завершить эксперимент и вернуть исходное состояние
ROLLBACK;