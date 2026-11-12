-- ПУНКТ 5. ПРОВЕРКА ОГРАНИЧЕНИЙ
-- Каждый опыт:
-- 1) выполнить BEGIN и ошибочную команду;
-- 2) показать Messages;
-- 3) отдельно выполнить ROLLBACK.


-- 1. NOT NULL: курс без названия
--Название курса обязательно. NOT NULL не позволяет сохранить NULL

BEGIN;

INSERT INTO courses (id, title, description, credits)
VALUES ('x-test', NULL, 'Test', 3);

ROLLBACK;


-- 2. CHECK: количество кредитов равно нулю
--CHECK запрещает нулевое и отрицательное количество кредитов

BEGIN;

INSERT INTO courses (id, title, description, credits)
VALUES ('x-test', 'Test', 'Test', 0);

ROLLBACK;


-- 3. CHECK: отрицательное количество лайков
--Количество лайков не может быть отрицательным

BEGIN;

UPDATE courses
SET likes = -1
WHERE id = 'api-design';

ROLLBACK;


-- 4. CHECK: имя студента короче двух символов
-- Имя студента должно содержать минимум два символа

BEGIN;

INSERT INTO students (name, email)
VALUES ('A', 'a@example.com');

ROLLBACK;


-- 5. UNIQUE: повторный email студента
--UNIQUE запрещает создавать двух студентов с одинаковым email»

BEGIN;

INSERT INTO students (name, email)
VALUES ('Dup Student', 'aigerim@example.com');

ROLLBACK;


-- 6. PRIMARY KEY: повторный идентификатор курса
-- Первичный ключ запрещает повторный идентификатор курса

BEGIN;

INSERT INTO courses (id, title, description, credits)
VALUES ('api-design', 'Test', 'Test', 3);

ROLLBACK;


-- 7. UNIQUE: повторная запись на один курс
-- Уникальная пара course_id и student_id запрещает повторную запись студента на тот же курс

BEGIN;

INSERT INTO enrollments (course_id, student_id)
VALUES ('modern-frontend', 1);

ROLLBACK;


-- 8. FOREIGN KEY: запись на несуществующий курс
-- Внешний ключ запрещает запись на курс, которого нет в courses

BEGIN;

INSERT INTO enrollments (course_id, student_id)
VALUES ('no-such-course', 1);

ROLLBACK;


-- 9. FOREIGN KEY: запись несуществующего студента
-- Внешний ключ запрещает запись студента, которого нет в students

BEGIN;

INSERT INTO enrollments (course_id, student_id)
VALUES ('web-security', 999);

ROLLBACK;


-- 10. RESTRICT: удаление курса с существующими записями
-- PostgreSQL 18: ожидается SQLSTATE 23001.
-- PostgreSQL 16–17: ожидается SQLSTATE 23503.
-- RESTRICT запрещает удаление курса, пока на него существуют записи

BEGIN;

DELETE FROM courses
WHERE id = 'modern-frontend';

ROLLBACK;


-- 11. CASCADE: удаление записей вместе со студентом
-- CASCADE удаляет записи вместе со студентом: количество уменьшилось с шести до трёх. После отката снова шесть

BEGIN;

SELECT count(*) AS enrollments_before
FROM enrollments;

DELETE FROM students
WHERE email = 'daniyar@example.com';

SELECT count(*) AS enrollments_after_delete
FROM enrollments;

ROLLBACK;

SELECT count(*) AS enrollments_after_rollback
FROM enrollments;


-- Итоговая проверка 6 / 3 / 6.

SELECT
    (SELECT count(*) FROM courses) AS courses,
    (SELECT count(*) FROM students) AS students,
    (SELECT count(*) FROM enrollments) AS enrollments;