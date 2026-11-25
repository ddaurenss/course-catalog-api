# course-catalog-api — Labs 7–8

FastAPI + SQLAlchemy 2.1 + PostgreSQL + Alembic. Решение лабораторной №7.
Подробное объяснение для защиты: [РАЗБОР.md](РАЗБОР.md).

## How to run

Нужны Python 3.11+ и PostgreSQL 16+. Один раз от суперпользователя PostgreSQL:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Из папки `course-catalog-api`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# При необходимости исправить порт и пароль в .env.
alembic upgrade head
psql -h localhost -p 5432 -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
python check_db.py
python check_models.py
alembic check
fastapi dev main.py
```

Swagger: http://localhost:8000/docs. В другом терминале с активным окружением:

```bash
python try_errors.py
python -m unittest -v
```

На этом Mac всё уже установлено: `.env` указывает на **localhost:5437/course_catalog**
в существующем контейнере `lab7-postgres`. База создана отдельно, данные Lab 6
на порту 55436 не изменялись. Для запуска достаточно:

```bash
cd course-catalog-api
source .venv/bin/activate
fastapi dev main.py
```

Если контейнер остановлен: `docker start lab7-postgres`. Для psql на этом Mac:
`"/Applications/pgAdmin 4.app/Contents/SharedSupport/psql"`; локально добавлять `-p 5437`.
`seed.sql` сбрасывает учебные данные до 6 курсов, 3 студентов, 6 записей,
сбрасывает identity и лайки; применять только при намеренном сбросе.
`.env` игнорируется git. `change-me` — учебный пароль, реальные пароли в git не добавляются.
`SQL_ECHO=true` в `.env` включает SQL и значения параметров для локальной отладки.
Переменная окружения `DATABASE_URL` имеет приоритет над `.env`.

## What changed in the API

- Курсы, студенты и записи хранятся в PostgreSQL; перезапуск сервера сохраняет данные.
- `POST /students`: `{"name":"Nurlan Abenov","email":"nurlan@example.com"}` → 201 и `id`.
- `POST /enrollments`: `{"courseId":"web-security","studentId":4}` → 201.
  Использовать реальный `id` из ответа создания студента.
- `GET /enrollments` использует JOIN, возвращает также `courseTitle`, `studentName`, `enrolledAt`.
- `GET /stats/courses` использует LEFT JOIN и `count(enrollments.id)`;
  курсы без записей имеют 0. На seed: ai-integration — 3, modern-frontend — 2,
  backend-fastapi — 1, остальные — 0.
- `GET /courses` сохраняет фильтр `is_elective`, сортировку `popular|title`,
  `page` и `page_size`; добавлен `level=beginner|intermediate|advanced`.
  В ответе есть обязательное поле `level`; в seed два beginner и четыре intermediate.
- `GET /courses/{id}` возвращает курс либо 404; `POST /courses/{id}/like` увеличивает лайки атомарно.
- Повторный email и повторная запись → 409; отсутствующие курс или студент → 404;
  невалидное имя/email/параметры → 422. Неизвестный IntegrityError не маскируется.
- Python использует snake_case, JSON — camelCase. Фронтенд по заданию не меняется:
  его прежний `studentName` в запросе записи теперь приводит к 422. Проверять через `/docs`.

## Migrations

| Команда | Назначение |
|---|---|
| `alembic upgrade head` | Применить недостающие миграции |
| `alembic downgrade -1` | Откатить последнюю миграцию |
| `alembic current` | Версия базы |
| `alembic heads` | Конечные вершины истории |
| `alembic history` | История миграций |
| `alembic revision --autogenerate -m "text"` | Черновик по отличиям моделей от базы |
| `alembic check` | Найти различия схемы и моделей |
| `alembic upgrade 0001:0002 --sql` | Просмотреть SQL без выполнения |
| `alembic stamp 0001` | Только отметить существующую схему Lab 6 как 0001 |
| `alembic stamp head` | Только отметить текущую конечную версию, без выполнения DDL |

История: `<base> → 0001 → 0002 (head)`. `0001` создаёт три таблицы и индекс.
`0002` добавляет `level`. В существующей базе Lab 6 нужно сначала подтвердить
совпадение исходной схемы с 0001, выполнить `stamp 0001`, затем `upgrade head`.
Нельзя делать `stamp head` на схеме Lab 6: head уже требует `level`.
На пустой базе используется только `upgrade head`.
Alembic запускается из корня API. Применять autogenerate без чтения файла нельзя.

## Experiment log

Все восемь опытов фактически выполнены 5 ноября 2026 в отдельной базе
`lab7_verify_20261105` на PostgreSQL 18.6. Полный вывод:
[experiments/lab7-verification.log](experiments/lab7-verification.log).

| № | Что сломали | Что увидели | Причина | Исправление |
|---|---|---|---|---|
| 1 | uq-шаблон `_key` заменён на `_uniq` | check_models показывает students_email_uniq только в моделях, students_email_key только в БД; также расходится составной UNIQUE | Имена в metadata и PostgreSQL различаются | Восстановлен `_key` |
| 2 | Убрали min_length у StudentIn, отправили имя N | HTTP 500; CheckViolation, students_name_check | Pydantic пропустил имя, CHECK в БД сохранил данные, неизвестное нарушение проброшено | Возвращён Field(min_length=2), снова 422 |
| 3 | students_email_key заменили на students_email_uniq в словаре | Повторный email → HTTP 500 | Реальное имя не найдено в словаре | Вернули students_email_key; снова 409 |
| 4 | Убрали NOT NULL у title, затем заменили text на varchar(100) | alembic check: modify_nullable, затем modify_type; ненулевой exit code | База разошлась с моделью | Восстановили NOT NULL и text |
| 5 | Добавили level сразу nullable=False в заполненную таблицу | NotNullViolation: column level contains null values; версия осталась 0001 | Для старых строк нет значения нового поля, DDL откатился | nullable=True → UPDATE → SET NOT NULL |
| 6 | Закомментировали import models в env.py | autogenerate предложил drop_table всех трёх таблиц и drop_index | Base.metadata пустая | Опасный черновик не применяли; удалили его и вернули импорт |
| 7 | Добавили phone в Student без миграции | alembic check: add_column students.phone | Модель опережает схему | Удалили экспериментальное поле |
| 8 | Создали 0003 и 0004 от 0002 | Две heads; upgrade head: Multiple head revisions; после merge одна 0005 | Разветвлённая история | Проверили merge, удалили три экспериментальных файла без применения; осталась 0002 |

Дополнительно проверены DuplicateTable при upgrade существующей схемы и `stamp 0001`,
цикл upgrade → downgrade → upgrade на заполненной таблице, отсутствие `level` после
отката, полный downgrade base → upgrade head → seed → check → API-тесты.
Экспериментальный runner требует специальное имя базы и сбрасывает её public schema.
Исходные schema/seed Lab 6 включены в `experiments/fixtures/`: для повторения
экспериментов достаточно этого репозитория. Повтор опытов:

```bash
DATABASE_URL=postgresql+psycopg://catalog_app:change-me@localhost:55436/lab7_verify_20261105 \
  python experiments/run_experiments.py
```

## Decisions

1. SQLSTATE 23505 одинаков для разных UNIQUE, а имя ограничения указывает конкретное
   правило и нужный ответ. Текст ошибки зависит от версии/языка. Проверка SELECT перед
   INSERT имеет гонку: другой запрос может вставить строку между проверкой и записью.
   Поэтому ловим IntegrityError при commit, делаем rollback и выбираем ответ по имени.
   Неизвестные нарушения пробрасываются как ошибки сервера.
2. `UPDATE ... SET likes = likes + 1 RETURNING ...` вычисляет значение внутри БД.
   PostgreSQL блокирует изменяемую строку и последовательно применяет обновления.
   Чтение и `course.likes += 1` в двух сессиях может дважды записать одно и то же число
   и потерять один лайк.
3. Новую NOT NULL-колонку нельзя сразу добавить в заполненную таблицу без значения
   для старых строк. В 0002 сначала разрешаем NULL, заполняем уровни по is_elective,
   затем запрещаем NULL. Все три шага выполняются в одной транзакции. level не имеет
   постоянного server_default. Downgrade удаляет колонку и её значения; повторный
   upgrade вычисляет их заново и не восстанавливает произвольные пользовательские уровни.

## Migration 0002 self-check

| Проверка | Результат |
|---|---|
| Цель и шаги | Да: только level, три последовательных шага |
| Данные | Да: шесть старых курсов сохранены, элективам beginner, остальным intermediate |
| Переименования/удаления | Да: upgrade ничего не удаляет и не переименовывает |
| Откат | Да: downgrade удаляет level; его пользовательские значения теряются, перед production нужен план восстановления |
| Проверка | Да: --sql прочитан; upgrade/downgrade/upgrade и чистое развёртывание прошли, alembic check без различий |
| История | Да: одна head 0002; миграция level сохраняется вместе с моделями и схемами API |
| Приложение | Да: level в модели, ответе, фильтре и seed; прежний studentName-контракт заменён studentId |

## Фактическая проверка и сдача

Python 3.13.16, SQLAlchemy 2.1.8, Alembic 1.20.1, psycopg 3.3.8.
Пять интеграционных тестов проходят на настоящем PostgreSQL. Они откатывают изменения
через внешнюю транзакцию и savepoint, включая commit внутри маршрутов.
Имена ограничений и индексов совпадают; начальные счётчики 6/3/6.
Локальное развёртывание: [experiments/local-start.log](experiments/local-start.log).
HTTP-проверка: [experiments/http-verification.log](experiments/http-verification.log):
5 из 5 ошибочных запросов, 10 конкурентных лайков (11 → 21), сохранение значения
после перезапуска сервера. Затем исходный seed восстановлен.
Обязательные восемь экспериментов и все пять бонусов выполнены; бонусы описаны отдельно ниже.
Репозиторий: https://github.com/ddaurenss/course-catalog-api.
Для сдачи передать преподавателю ссылку на этот репозиторий через LMS или учебный чат.


## Проверка по критериям оценивания — 12 ноября 2026

Таблица ниже относится к обязательной части. Все пять бонусных заданий добавлены
отдельно в разделе Bonus и не меняют эту шкалу из 10 баллов.

| Критерий из задания | Баллы | Реализация и подтверждение |
|---|---:|---|
| Подключение и модели | 2 | config.py, .env.example, db.py, naming_convention, три ORM-модели; check_db и check_models |
| Маршруты на SQLAlchemy | 2 | Фильтры is_elective/level, сортировка, страницы, UPDATE RETURNING для лайка; студенты, JOIN записей, LEFT JOIN и count(Enrollment.id) для статистики |
| Ошибки базы как HTTP-ответы | 1 | Сопоставление по constraint_name, 409/404; try_errors.py проверяет 5 из 5, Pydantic возвращает 422 |
| Alembic | 2 | env.py, 0001, stamp существующей схемы, 0002 в три шага; одна head, check; upgrade/downgrade/upgrade |
| Эксперименты и самопроверка | 2 | Восемь строк Experiment log с наблюдениями, причинами, исправлениями; семь строк Migration 0002 self-check |
| Репозиторий и README | 1 | Инструкция с нуля, изменения API, три Decisions; восемь содержательных коммитов Lab 7 плюс проверка готовности к сдаче |
| Всего по шкале задания | **10** | Итоговую оценку выставляет преподаватель |

Свежие результаты: [criteria-2026-11-12.log](experiments/criteria-2026-11-12.log).
В логе ошибки ожидаемы только внутри восьми контролируемых экспериментов;
итоговая строка подтверждает успешное завершение и восстановление рабочего состояния.

Проверка создания базы с нуля и настоящего HTTP-сервера:
[clean-start-2026-11-12.log](experiments/clean-start-2026-11-12.log),
[http-2026-11-12.log](experiments/http-2026-11-12.log).
Проверка рабочей базы: [working-db-2026-11-12.log](experiments/working-db-2026-11-12.log).
Разрушающие проверки проводятся в отдельной `lab7_verify_20261112`; рабочая `course_catalog`
и проекты Lab 6/фронтенд не пересоздаются.

Повторить эксперименты на этом Mac (от суперпользователя один раз создать
`CREATE DATABASE lab7_verify_20261112 OWNER catalog_app;`):

```bash
source .venv/bin/activate
export DATABASE_URL=postgresql+psycopg://catalog_app:change-me@localhost:5437/lab7_verify_20261112
python experiments/run_experiments.py
python experiments/verify_http.py
unset DATABASE_URL
```

Для проверки рабочей базы перед защитой:

```bash
python check_db.py
python check_models.py
alembic current
alembic heads
alembic check
fastapi dev main.py
# Во втором терминале:
python try_errors.py
```


## Bonus

По дополнительному запросу выполнены **все пять** бонусных заданий Lab 7.
Объяснение каждого для защиты: [BONUS.md](BONUS.md).
Реальный вывод: [bonus-2026-11-12.log](experiments/bonus-2026-11-12.log).

| № | Бонус | Проверенный результат |
|---|---|---|
| 1 | CHECK и op.f | Autogenerate дал pass; ручной CHECK отклонил expert; откат без op.f дал удвоенное имя, после исправления прошёл |
| 2 | Переименование description → summary | Черновик add/drop заменён alter_column; все шесть описаний сохранены при upgrade и downgrade |
| 3 | N+1 | Lazy: 7 запросов; selectinload: 2; оба варианта возвращают 6 записей |
| 4 | Lost update | Две сессии читают 11: Python-арифметика даёт 12, SQL-выражение — 13 |
| 5 | passive_deletes / CASCADE | Без параметра — NotNullViolation; с ним — 2 студента / 5 записей; seed затем восстановлен |

Опыты запускаются одной командой `python experiments/run_bonus.py` с DATABASE_URL,
указывающим на отдельную `lab7_bonus_20261112` (полные команды в BONUS.md).
Изменения моделей и 0003 выполняются только во временной копии проекта.
Артефакты миграций сохранены как `.py.txt` в `experiments/bonus_artifacts`,
чтобы их можно было показать преподавателю без добавления лишних версий Alembic.
В рабочем проекте остаются две миграции и исходные модели; обязательные тесты
проходят после бонусов. Дополнительные баллы определяет преподаватель.

# Lab 8 — GraphQL Alongside REST

## How to run

Нужны Python 3.11+, PostgreSQL 16+ и Node.js. Для чистой базы создай роль и базу
(если роль уже есть, повторно её создавать не нужно):

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Из `course-catalog-api` создай окружение, установи зависимости, настрой `.env`,
примени миграции и загрузи учебные данные:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Проверь порт и пароль в DATABASE_URL.
alembic upgrade head
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
alembic check
fastapi dev main.py
```

Если используешь нестандартный порт PostgreSQL, укажи его и в `DATABASE_URL`, и
в аргументах `psql`. `seed.sql` сбрасывает таблицы и загружает 6 курсов,
3 студентов и 6 записей. Запускай его, когда нужен именно такой набор данных.

REST-документация: http://localhost:8000/docs. GraphiQL: http://localhost:8000/graphql.
Проверки выполняются при запущенном API:

```bash
python try_errors.py
python try_graphql.py
python try_n_plus_1.py
python measure.py
python try_protection.py
python -m unittest -v
```

Для двух frontend-страниц создай в корне `course-catalog/.env.local` (не добавляй
его в Git):

```dotenv
API_URL=http://localhost:8000
```

Затем из `course-catalog` выполни `npm install` и `npm run dev`. Страницы:
http://localhost:3000/my-courses-rest и http://localhost:3000/my-courses.

## What changed in the API

- Правила и ожидаемые ошибки находятся в `services.py`. REST-преобразование в
  [Problem Details (RFC 9457)](https://www.rfc-editor.org/rfc/rfc9457) выполняет
  `problem.py`; ответы имеют `application/problem+json`, а `type` указывает вид
  ошибки. Pydantic-ошибка 422 остаётся стандартным ответом FastAPI.
- Strawberry обслуживает GraphQL на `/graphql`; открытие этого адреса в браузере
  показывает GraphiQL — редактор запросов и документацию схемы.
- Query читает выбранные клиентом поля. Ошибка текста/выполнения GraphQL обычно
  приходит в `errors` при HTTP 200. Ожидаемые ошибки бизнес-правил приходят в
  `data.<mutation>.userErrors`; неожиданные ошибки остаются в `errors`.
- Мутации `enroll` и `likeCourse` используют общие сервисы с REST. `userErrors`
  возвращает код и сообщение ожидаемой ошибки.
- Middleware добавляет `X-SQL-Queries` — количество SQL-команд, выполненных для
  HTTP-запроса. Заголовок нужен, чтобы измерять N+1, а не оценивать нагрузку только
  по времени или размеру ответа.
- DataLoaders, созданные на каждый GraphQL-запрос, пакетно загружают связи и
  уменьшают число запросов. Защита ограничивает глубину пятью уровнями, число
  aliases — десятью, `limit` — диапазоном 1–100, проверяет числовой `id` и скрывает
  внутренние ошибки. `GRAPHQL_INTROSPECTION` управляет introspection; её отключение
  не заменяет авторизацию.
- Добавлены REST-маршруты `GET /students/{id}` и
  `GET /students/{id}/enrollments` для страницы «Мои курсы».

## Example queries

Запрос страницы «Мои курсы» (в GraphiQL Variables передать `{"id":"2"}`):

```graphql
query MyCourses($id: ID!) {
  student(id: $id) {
    name
    enrollments { id course { title credits level } }
  }
}
```

Запись студента 3 на `web-security`:

```graphql
mutation Enroll($input: EnrollInput!) {
  enroll(input: $input) {
    enrollment { id enrolledAt course { title } }
    userErrors { code message }
  }
}
```

Variables: `{"input":{"courseId":"web-security","studentId":"3"}}`.
При успехе `enrollment` заполнен, а `userErrors` пуст. Повтор того же запроса
возвращает обычный GraphQL-ответ с бизнес-ошибкой:

```json
{
  "data": {
    "enroll": {
      "enrollment": null,
      "userErrors": [
        {
          "code": "ALREADY_ENROLLED",
          "message": "Student is already enrolled in this course"
        }
      ]
    }
  }
}
```

## REST vs GraphQL comparison

Измерение `measure.py` для студента 2 на исходном наборе. Размер ответа может
отличаться из-за времени записи в базу; остальные числа воспроизводятся.

| Критерий | REST | GraphQL | Источник |
|---|---|---|---|
| Запросы и раунды на экран | 5 запросов, 2 раунда | 1 запрос, 1 раунд | `measure.py` |
| Байты ответов | 1130 | 339 | `measure.py` |
| SQL-запросы на экран | 5 | 3 | `X-SQL-Queries`, `measure.py` |
| Рост SQL при вложенной выборке | Для страницы 1 запрос на студента, 1 на записи и по запросу на курс | Без DataLoader было 7→27 и 7→24; с DataLoader 3→3 | `try_n_plus_1.py` |
| Ошибка текста запроса | REST использует URL/параметры и HTTP-статус | Обычно HTTP 200 и `errors`; клиент обязан проверять `errors` | опыты 1 и 8 |
| Повторная запись | 409, `application/problem+json` | HTTP 200, код `ALREADY_ENROLLED` в `userErrors` | `try_errors.py`, `try_graphql.py` |
| HTTP-кэш | GET-ответы можно кэшировать стандартными HTTP-механизмами | POST обычно не кэшируется обычным HTTP-кэшем; GraphQL query можно передавать GET, но mutation — только POST | лекция, раздел 14 |
| Защита дорогих запросов | Ограничения заданы в маршрутах и параметрах | Глубина ≤5, aliases ≤10, `limit` и `id` проверяются, внутренние ошибки скрываются | опыты 6 и 7 |

**Вывод.** REST удобен для отдельных ресурсов и стандартного HTTP-кэширования.
Для экрана «Мои курсы» GraphQL уменьшил число сетевых запросов с 5 до 1 и число
байтов с 1130 до 339, потому что клиент запросил только нужные поля. DataLoader
удержал число запросов базы на уровне 3 при росте набора с 3 до 20 студентов.
Обе схемы полезны: REST остаётся простым для фиксированных ресурсов, а GraphQL
подходит для экранов с вложенными данными и разными наборами полей.

## Experiment log

| # | Опыт | Что увидел | Причина | Как исправил |
|---|---|---|---|---|
| 1 | Опечатка `titel`; аргумент `is_elective` | HTTP 200, `data: null`, ошибка с подсказкой `title` / `isElective` | GraphQL проверяет имя поля и аргумента по схеме; Python snake_case преобразуется в camelCase | Исправил запрос на `title` и `isElective`; клиент проверяет `errors` |
| 2 | Убрал `\| None` у `course`, запросил отсутствующий курс | Нарушилось обещание non-null; ошибка поднялась к `data`; с MaskErrors клиент видит `Unexpected error.` | Non-null в схеме — обещание, что поле не вернёт null; ошибка поля может обнулить родителя | Вернул `CourseType \| None` |
| 3 | Отправил `likeCourse` через GET | HTTP 400, текст `mutations are not allowed when using GET`; лайк не изменился | GET должен быть безопасным и не менять состояние | Мутации отправляются POST |
| 4 | Lazy loading на 3 и 20 студентах | Было 7/7 SQL-запросов на 3 студентах и 27/24 на 20 | Отдельные lazy-запросы для отношений создают N+1 | Добавил пакетную загрузку DataLoader в опыте 5 |
| 5 | Batch-функция вернула строки в порядке БД, не ключей | Для 3 ключей студентов пришло 6 записей и WrongNumberOfResultsReturned; при совпавшей длине несколько записей получили чужой курс | DataLoader связывает результаты с ключами по позиции; порядок SQL-строк не гарантирует порядок ключей | Сгруппировал строки по значению ключа и вернул результат в порядке `keys` |
| 6 | Глубокий запрос, 12 aliases, плохие limit/id, introspection — до и после защиты | Без защиты цикл и 12 мутаций прошли; лайки выросли 11→23 за запрос с 24 SQL-командами; клиенту показывались детали SQL-ошибок. С защитой: depth 5, aliases 10, `limit`/`id` проверены, flood отклонён с 0 SQL | Неограниченные глубина и aliases позволяют запускать дорогие запросы; сырые исключения раскрывают внутренности | Добавил лимит глубины, aliases, проверки аргументов и MaskErrors |
| 7 | Отключил introspection и опечатался в поле | `__schema` отклонён; обычный запрос работал; подсказка `Did you mean` всё ещё раскрыла похожие поля | Introspection скрывает полную схему, но не является авторизацией и не скрывает ответы проверки имён | Вернул настройку `GRAPHQL_INTROSPECTION=true`; доступ к данным требует авторизации |
| 8 | Опечатка в frontend query, убрал проверку `errors`, остановил API | `GraphQLRequestError` с причиной; затем `Cannot destructure property 'student' ... null`; при остановленном API — `fetch failed` | `errors` может прийти при HTTP 200; без проверки видна только последующая ошибка; без соединения ответа нет | Восстановил проверку GraphQL `errors` и запустил API |

## Decisions

- Правила находятся в `services.py`, чтобы REST и GraphQL не реализовывали их
  отдельно. REST переводит код ошибки в HTTP Problem Details, GraphQL — в
  `userErrors`. При добавлении нового кода нужно добавить соответствующий перевод
  в REST и обработать его в нужной GraphQL-мутации.
- DataLoaders создаются в `Context` на каждый запрос, чтобы кэш не переживал запрос
  и не смешивал результаты разных клиентов. Batch-функция группирует строки по
  ключу, потому что порядок строк из БД не обязан совпадать с порядком ключей.
- `check_limit` и `parse_id` дают клиенту понятный ответ на ожидаемые ошибки
  аргументов. `MaskErrors` скрывает детали непредвиденных ошибок, например SQL и
  параметры. Лимиты глубины и aliases ограничивают объём работы до выполнения
  запроса; это два уровня защиты с разными задачами.
