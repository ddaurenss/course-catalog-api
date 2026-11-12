-- ПУНКТ 7. ДВЕ ВСТАВКИ И ОТКАТ
-- База: course_catalog


-- БЛОК 1. Проверка перед опытом
-- Ожидается 0.
SELECT count(*) AS students_before
FROM students
WHERE email = 'transaction.demo@example.com';


-- БЛОК 2. Начать транзакцию и создать студента
BEGIN;

INSERT INTO students (name, email)
VALUES ('Transaction Demo', 'transaction.demo@example.com')
RETURNING id, name, email;


-- БЛОК 3. Убедиться, что первая вставка выполнена
-- Внутри своего соединения видим созданного студента.
SELECT id, name, email
FROM students
WHERE email = 'transaction.demo@example.com';


-- БЛОК 4. Вторая вставка: несуществующий курс
-- Ожидается ошибка внешнего ключа, SQLSTATE 23503.
INSERT INTO enrollments (course_id, student_id)
SELECT 'no-such-course', id
FROM students
WHERE email = 'transaction.demo@example.com';


-- БЛОК 5. Проверка состояния после ошибки
-- Ожидается SQLSTATE 25P02:
-- current transaction is aborted.
SELECT count(*) FROM students;


-- БЛОК 6. Выполнить ОТДЕЛЬНО после ошибки
ROLLBACK;


-- БЛОК 7. Проверить результат отката
-- Ожидается 0: первая вставка тоже отменена.
SELECT count(*) AS students_after_rollback
FROM students
WHERE email = 'transaction.demo@example.com';


-- БЛОК 8. Проверить исходные количества
-- Ожидается 6 / 3 / 6.
SELECT
    (SELECT count(*) FROM courses) AS courses,
    (SELECT count(*) FROM students) AS students,
    (SELECT count(*) FROM enrollments) AS enrollments;