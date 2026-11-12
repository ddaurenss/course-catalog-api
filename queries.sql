-- Lab 6 — Step 4: SQL queries for API routes
-- Изменения отменяются через ROLLBACK.



-- 1. GET /courses — первая страница
-- Обязательные курсы, сортировка по популярности.
-- Ожидается: 3 курса с 24, 21 и 19 лайками.


SELECT id, title, credits, likes
FROM courses
WHERE is_elective = false
ORDER BY likes DESC, id
LIMIT 3 OFFSET 0;

-- 1b. GET /courses — вторая страница
-- Ожидается: databases-postgresql, 15 лайков.


SELECT id, title, credits, likes
FROM courses
WHERE is_elective = false
ORDER BY likes DESC, id
LIMIT 3 OFFSET 3;


-- 2. GET /courses/{course_id} — существующий курс
-- Ожидается: api-design, 4 кредита, true, 11 лайков.

SELECT id, title, credits, is_elective, likes
FROM courses
WHERE id = 'api-design';


-- 2b. GET /courses/{course_id} — отсутствующий курс
-- Ожидается: 0 строк. Будущий API возвращает HTTP 404.
-- 

SELECT id, title, credits, is_elective, likes
FROM courses
WHERE id = 'no-such-course';


-- 3 и 3b. POST /courses/{course_id}/like
-- Существующий курс: 12 лайков.
-- Отсутствующий курс: 0 обновлённых строк.
-- После ROLLBACK у api-design снова 11 лайков.

BEGIN;

-- 3. Увеличить лайки существующего курса
UPDATE courses
SET likes = likes + 1
WHERE id = 'api-design'
RETURNING id, likes;

-- 3b. Попробовать обновить отсутствующий курс
UPDATE courses
SET likes = likes + 1
WHERE id = 'no-such-course'
RETURNING id, likes;

ROLLBACK;


-- 4. POST /enrollments — записать студента на курс
-- Ожидается: новая запись студента 3 на web-security.
-- После ROLLBACK запись отменяется.
-- Выданный ID может отличаться при повторных запусках.


BEGIN;

INSERT INTO enrollments (course_id, student_id)
VALUES ('web-security', 3)
RETURNING id, course_id, student_id;

ROLLBACK;


-- 5. GET /enrollments — список записей
-- JOIN добавляет имя студента и название курса.
-- Ожидается: 6 строк.

SELECT
    e.id,
    s.name AS student,
    c.title AS course
FROM enrollments e
JOIN students s ON s.id = e.student_id
JOIN courses c ON c.id = e.course_id
ORDER BY e.id;


-- 6. Статистика по курсам, включая курсы без записей
-- Отдельного маршрута API для этой статистики пока нет.
-- Ожидается: 3, 2, 1, 0, 0, 0.

SELECT
    c.id,
    count(e.id) AS enrolled
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.id
GROUP BY c.id
ORDER BY enrolled DESC, c.id;