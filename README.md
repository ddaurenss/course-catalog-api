# course-catalog-db

Лабораторная №6: PostgreSQL Database Schema. Frontend `course-catalog` и backend `course-catalog-api` не изменяются: подключение SQLAlchemy относится к следующей лабораторной.

## How to run

Нужны PostgreSQL 16+ и psql. На этом Mac клиент найден по пути `/Applications/pgAdmin 4.app/Contents/SharedSupport/psql`; можно добавить эту папку в PATH.

Один раз в psql от суперпользователя (`psql postgres` на macOS):

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
CREATE DATABASE idx_demo OWNER catalog_app;
CREATE DATABASE norm_demo OWNER catalog_app;
```

Из каталога проекта:

```bash
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f schema.sql
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f queries.sql
```

`change-me` — учебный пароль. `schema.sql` удаляет старые таблицы вместе с данными; повторный чистый запуск: schema → seed → queries. seed рассчитан на пустые таблицы; повторный запуск должен нарушить уникальность. Транзакция seed предотвращает частичную загрузку.

Проверка:

```sql
SELECT current_database(), current_user;
SHOW server_version;
\dt
\d courses
\d students
\d enrollments
SELECT (SELECT count(*) FROM courses) AS courses,
       (SELECT count(*) FROM students) AS students,
       (SELECT count(*) FROM enrollments) AS enrollments;
```

Ожидается 6 / 3 / 6, два элективных курса, студенты 1, 2, 3. После `queries.sql` api-design по-прежнему имеет 11 лайков. Identity может иметь пропуски: nextval не откатывается.

## Schema

```mermaid
erDiagram
    COURSES ||--o{ ENROLLMENTS : "course enrollments"
    STUDENTS ||--o{ ENROLLMENTS : "student enrollments"
    COURSES {
        text id PK "course slug"
        text title
        text description
        integer credits
        boolean is_elective
        integer likes
    }
    STUDENTS {
        bigint id PK "generated always as identity"
        text name
        text email UK
    }
    ENROLLMENTS {
        bigint id PK "generated always as identity"
        text course_id FK
        bigint student_id FK
        timestamptz enrolled_at
    }
```

Курсы и студенты хранятся независимо. enrollments связывает их отношением многие-ко-многим через две связи один-ко-многим. Составная уникальность `(course_id, student_id)` запрещает повторную запись на один курс.

## Design decisions

1. `courses.id` — текстовый slug: совпадает с URL и данными прежнего API, читается человеком; длиннее числа и сложнее переименовывается. `students.id` — bigint identity: стабильный компактный ключ, независимый от имени/email, но сам по себе не объясняет, кто студент.
2. `RESTRICT` сохраняет курс, пока на него есть записи. `CASCADE` удаляет записи удалённого студента автоматически, не затрагивая курсы.
3. `timestamptz` хранит момент времени и отображает его в часовом поясе сессии; исходное название пояса не сохраняется. `timestamp` не определяет однозначный момент между поясами. `text` не вводит произвольный лимит длины; нужные бизнес-правила задаются CHECK.

## Constraint violation log

Команды: `psql -h localhost -U catalog_app -d course_catalog -f experiments/constraints.sql`. Файл намеренно продолжает работу после ошибок и включает `\set VERBOSITY verbose`. Ниже — ожидаемые коды по заданию; фактический статус запуска см. в конце README.

| # | Нарушение | SQLSTATE | Constraint / column | API response |
|---|---|---|---|---|
| 1 | NULL title | 23502 | courses.title (COLUMN NAME) | 422; 500, если пропустила валидация кода |
| 2 | credits = 0 | 23514 | courses_credits_check | 422 |
| 3 | likes = -1 | 23514 | courses_likes_check | 500: счётчик меняет наш код |
| 4 | Имя из одной буквы | 23514 | students_name_check | 422 |
| 5 | Повтор email | 23505 | students_email_key | 409 |
| 6 | Повтор course id | 23505 | courses_pkey | 409 |
| 7 | Повтор пары курс/студент | 23505 | enrollments_course_id_student_id_key | 409 |
| 8 | Несуществующий курс | 23503 | enrollments_course_id_fkey | 404 |
| 9 | Несуществующий студент | 23503 | enrollments_student_id_fkey | 404: student not found |
| 10 | Удаление курса с записями | 23001 (18), 23503 (16–17) | enrollments_course_id_fkey | 409 |
| 11 | Удаление Daniyar | успех | enrollments_student_id_fkey: CASCADE | 6 → 3, после ROLLBACK снова 6 |
| + | Ручной identity id | 428C9 | students.id GENERATED ALWAYS | 500 |

HTTP здесь — проектируемое поведение будущего API, а не ответы изменённого backend. Ошибки определяются по SQLSTATE и полям диагностики, а не по тексту сообщения.

Pydantic даёт клиенту понятный ранний ответ, но к БД обращаются также SQL-консоль, импорт, другие сервисы и скрипты. Поэтому ограничения БД защищают целостность независимо от пути записи; валидация в API не заменяет CHECK/UNIQUE/FK.

## Index: EXPLAIN before and after

Запуск: `psql -h localhost -U catalog_app -d idx_demo -v ON_ERROR_STOP=1 -f experiments/index.sql > experiments/index.log 2>&1`.
Сценарий защищён проверкой имени БД, пересоздаёт схему только в idx_demo, временно удаляет итоговый индекс для честного сравнения, загружает 500 / 20000 / 50000 строк и делает по три замера до и после.

Запрос: `SELECT * FROM enrollments WHERE student_id = 777;`.

| Показатель | До индекса (ожидается) | После индекса (ожидается) |
|---|---|---|
| Access method | Seq Scan | Bitmap Heap/Index Scan или Index Scan |
| cost | фактический вывод в index.log | фактический вывод в index.log |
| Rows Removed by Filter | 49997 | обычно отсутствует |
| Execution Time | минимум трёх запусков в index.log | минимум трёх запусков в index.log |

Ожидаемые формы планов, НЕ фактические замеры:

```text
Seq Scan on enrollments
  Filter: (student_id = 777)
```

```text
Bitmap Heap Scan on enrollments
  Recheck Cond: (student_id = 777)
  -> Bitmap Index Scan on enrollments_student_id_idx
       Index Cond: (student_id = 777)
```

1. UNIQUE(email) автоматически создаёт индекс; UNIQUE(course_id, student_id) помогает искать по первому столбцу course_id. Сам FOREIGN KEY индекс не создаёт. Поиск только по student_id в данном эксперименте требует отдельного индекса (конкретное решение всегда принимает планировщик).
2. На шести строках Seq Scan может стоить дешевле обращения к индексу; на 50000 строках при выборе трёх строк индекс сокращает чтение. Проверка малой таблицы: `ANALYZE courses; EXPLAIN SELECT * FROM courses WHERE id = 'api-design';` в course_catalog.
3. Индекс ускоряет получение записей одного студента и поиск дочерних записей при каскадном удалении студента. Цена — дополнительное место и обслуживание при изменении данных; размер выводит сценарий.

## Transaction

Ошибка второй вставки: `psql -h localhost -U catalog_app -d course_catalog -f experiments/transaction.sql`.
Ожидается: первый INSERT успешен, второй даёт 23503, SELECT внутри аварийной транзакции — 25P02. После ROLLBACK count Madina равен 0: отменён и первый INSERT. Без общей транзакции студент сохранился бы без записи на курс.

Успешный сценарий: открыть два psql, подключённых к course_catalog как catalog_app. В окне A:

```sql
BEGIN;
INSERT INTO students (name,email) VALUES ('Madina Ospanova','madina@example.com');
INSERT INTO enrollments (course_id,student_id)
SELECT 'web-security',id FROM students WHERE email = 'madina@example.com';
```

В окне B до COMMIT:

```sql
SELECT count(*) FROM students WHERE email = 'madina@example.com';
```

Ожидается 0. Выполнить `COMMIT;` в A, повторить SELECT в B: ожидается 1. Две вставки становятся видимы вместе. Проверить:

```sql
SELECT s.name,c.title FROM enrollments e
JOIN students s ON s.id=e.student_id JOIN courses c ON c.id=e.course_id
WHERE s.email='madina@example.com';
SHOW default_transaction_isolation;
```

Ожидается Madina Ospanova / Web Security Essentials, изоляция `read committed`, всего 4 студента и 7 записей. Пока A не завершена, B не видит её изменений. Держать транзакции короткими: они удерживают блокировки. Перед повторным запуском schema.sql завершить транзакции в обоих окнах.
