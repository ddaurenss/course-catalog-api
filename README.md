# Course Catalog API — Lab 4

Standalone FastAPI backend demonstrating Pydantic models, course lookup, filtering, sorting, and pagination through dependency injection.

## Run locally

Requires Python 3.10+ and Git. On this Mac, Python 3.13 was installed with `brew install python@3.13`.

From the `course-catalog-api` folder on macOS/Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
fastapi dev main.py
```

Use `python3` instead of `python3.13` if it is already version 3.10 or newer. Activate the environment in each new terminal.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
fastapi dev main.py
```

Open http://127.0.0.1:8000/docs. There are exactly three application routes: `GET /`, `GET /courses`, and `GET /courses/{course_id}`. Alternative documentation: `/redoc`; machine-readable schema: `/openapi.json`.

Data stays in memory and comes from the six courses in the Lab 4 handout. The existing Next.js book catalog is separate; connecting the frontend belongs to Lab 5. JSON uses `is_elective`, not the frontend's `isElective`.

## What was verified

The automated checks in `test_api.py` cover these expected responses:

| Request | Expected response |
| --- | --- |
| `/` | 200, `{"message":"Course Catalog API is running"}` |
| `/courses` | 200, ai-integration, modern-frontend, web-security, backend-fastapi, databases-postgresql, api-design |
| `/courses/web-security` | 200, Web Security Essentials with credits=4, is_elective=false, likes=21 |
| `/courses/nope` | 404, `{"detail":"Course not found"}` |
| `/courses?is_elective=true` | ai-integration, api-design |
| `/courses?is_elective=false` | modern-frontend, web-security, backend-fastapi, databases-postgresql |
| `/courses?sort=title` | ai-integration, api-design, backend-fastapi, modern-frontend, databases-postgresql, web-security |
| `/courses?page=1&page_size=2` | ai-integration, modern-frontend |
| `/courses?page=2&page_size=2` | web-security, backend-fastapi |
| `/courses?page=3&page_size=2` | databases-postgresql, api-design |
| `/courses?page=4&page_size=2` | `[]` |
| `/courses?is_elective=false&sort=title&page=2&page_size=2` | databases-postgresql, web-security; filtering and sorting precede pagination |
| `/courses?sort=banana` | 422: unsupported sort (bonus) |
| `/courses?page=0` | 422: page must be at least 1 (bonus) |
| `/courses?page_size=1000` | 422: page_size must be between 1 and 100 (bonus) |
| `/docs`, `/redoc`, `/openapi.json` | 200; OpenAPI exposes exactly three GET operations and the Course schema |

Run the acceptance checks after activating `.venv`:

```bash
python -m unittest -v
```

Verified locally on Python 3.13.16 with FastAPI 0.143.0: all 7 test methods passed. FastAPI is pinned to the verified version in `requirements.txt`.

The actual server was also started with `fastapi dev main.py`. HTTP checks confirmed 200 responses from `/`, `/docs`, `/redoc`, and `/openapi.json`; page 2 returned `web-security` and `backend-fastapi`; `/courses/nope` returned the expected 404 JSON. Swagger's interactive controls still need to be exercised manually in your browser before submission.

The tests also verify Pydantic defaults (`is_elective=False`, `likes=0`), conversion of `credits="5"` to 5, rejection of `credits="five"`, rejection of invalid query types, and preservation of the original data order.

For the manual Swagger verification required by the lab, open `/docs`, expand `GET /courses`, choose **Try it out**, enter the parameters from the table, and select **Execute**. Inspect the request URL, response body, and status code. Repeat for `/courses/{course_id}` with `web-security` and `nope`, then inspect **Schemas → Course**.

## Files and implementation

- `models.py`: the Pydantic `Course` model.
- `data.py`: six courses, `get_all_courses()` returning a list copy, and `find_course()`.
- `main.py`: routes and `pagination()`; offset is calculated only in the dependency.
- `test_api.py`: repeatable acceptance checks using FastAPI TestClient and unittest.
- `requirements.txt`: FastAPI with its standard server and CLI dependencies.

No database, frontend integration, or extra `/stats` route is required. The two implemented bonuses are the sort dropdown using `Literal` and pagination constraints using `Query`.

## GitHub submission

This folder is its own Git repository. `.venv/` and Python cache files are ignored. Review the meaningful implementation commits with `git log --oneline`.

Create an empty GitHub repository named `course-catalog-api`, then run from this folder (replace `YOUR_USERNAME`):

```bash
git remote add origin https://github.com/YOUR_USERNAME/course-catalog-api.git
git push -u origin main
```

Submit that repository link through your instructor's requested channel.
