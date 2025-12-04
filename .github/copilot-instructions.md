# Copilot / AI Agent Instructions — LukestAWS URL Shortener

These notes are targeted to AI coding agents working on this repository. They focus on the concrete, discoverable patterns and workflows in the codebase so you can be productive immediately.

**Big Picture**
- **Runtime:** Python 3.12 (see `Dockerfile`).
- **Web framework:** FastAPI (`main.py`) with `uvicorn` as the server.
- **Containers:** `Dockerfile` for the app and `docker-compose.yml` orchestrates `api` + `db` (Postgres 16-alpine).
- **Current state:** `main.py` implements a Day-1 in-memory store (`DB: dict[str, str]`) and endpoints. `docker-compose.yml` already wires a Postgres service and `DATABASE_URL`, but the app currently does not use Postgres yet (see comment in `main.py`).

**Key files to reference**
- `main.py` — FastAPI routes and in-memory data model. Important endpoints: `POST /shorten` and `GET /r/{code}`.
- `requirements.txt` — pinned dependencies (`fastapi`, `uvicorn[standard]`, `pydantic`).
- `Dockerfile` — multi-stage image, non-root user (UID/GID `1001`), `CMD` uses `uvicorn main:app`.
- `docker-compose.yml` — service names (`api`, `db`), network `appnet`, volume `postgres_data`, and `DATABASE_URL` environment variable.

**Concrete patterns & conventions**
- **Port & host:** App exposes port `8000` (`uvicorn` in `Dockerfile`, `ports: "8000:8000"` in compose).
- **Non-root container user:** Build and run the container with UID/GID `1001` — keep file ownership and runtime-user sensitive changes consistent with this value.
- **Healthchecks:** Both `api` and `db` define healthchecks in `docker-compose.yml`. Keep new services aligned with those healthcheck conventions.
- **In-memory -> persistent migration:** `main.py` intentionally uses a typed `DB: dict[str, str]` and a comment notes Postgres is next. When adding DB integration, reuse the `DATABASE_URL` env var defined in `docker-compose.yml`.
- **Type hints:** Code uses modern typing (PEP 585 style e.g. `dict[str, str]`) and `pydantic` v2 — prefer matching these patterns.

**Developer workflows (commands discovered in repo)**
- Run locally without Docker:
  - Install deps: `pip install -r requirements.txt`
  - Start server: `uvicorn main:app --host 0.0.0.0 --port 8000`
  - API docs: `http://localhost:8000/docs` (Swagger) and `http://localhost:8000/redoc` (Redoc).
- With Docker Compose (recommended for full stack):
  - Build + run: `docker compose up --build`
  - The `api` service depends on the `db` service and uses `DATABASE_URL=postgresql://shortener:shortener@db:5432/shortener`.

**What to change and how to test changes (practical examples)**
- To implement Postgres integration: read `docker-compose.yml` for credentials and `DATABASE_URL`. Add a small wrapper that on startup reads `DATABASE_URL` and migrates/creates required table(s). Keep the `GET /r/{code}` and `POST /shorten` route signatures identical to preserve the API contract.
- To run quick local tests for routes, issue HTTP requests against `http://localhost:8000/shorten` and `http://localhost:8000/r/{code}`. Example request body for `POST /shorten` (JSON): `{ "url": "https://example.com" }` (Pydantic `HttpUrl` is validated).

**Repository-specific gotchas / notes**
- The project assumes Python 3.12 semantics (see `Dockerfile`). Avoid introducing syntax incompatible with 3.12.
- The `Dockerfile` copies installed site-packages from the build stage into the final image. When adding new dependencies, update `requirements.txt` and rebuild the image.
- Do not remove or change the `USER appuser` configuration unless you update tests and the compose `user:` setting.

If any detail above is unclear or you want more examples (e.g., a starter migration script or a sample DB access module), say which area to expand and I will iterate the instructions.
