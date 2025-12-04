# Copilot / AI Agent Instructions — LukestAWS URL Shortener

These notes are targeted to AI coding agents working on this repository. They focus on the concrete, discoverable patterns and workflows in the codebase so you can be productive immediately.

**Big Picture**

**Key files to reference**

**Concrete patterns & conventions**

**Developer workflows (commands discovered in repo)**
  - Install deps: `pip install -r requirements.txt`
  - Start server: `uvicorn main:app --host 0.0.0.0 --port 8000`
  - API docs: `http://localhost:8000/docs` (Swagger) and `http://localhost:8000/redoc` (Redoc).
  - Build + run: `docker compose up --build`
  - The `api` service depends on the `db` service and uses `DATABASE_URL=postgresql://shortener:shortener@db:5432/shortener`.

**What to change and how to test changes (practical examples)**

**Repository-specific gotchas / notes**

If any detail above is unclear or you want more examples (e.g., a starter migration script or a sample DB access module), say which area to expand and I will iterate the instructions.
