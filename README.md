# LukestAWS URL Shortener — Minimal Rebuild

This repository contains a minimal FastAPI URL shortener intended for
fast builds and straightforward deployment to Fly (or local Docker).

Quick start (local)

1. Build and run with Docker Compose:

```bash
docker compose up --build
```

2. Open http://localhost:8000 and use the `/shorten` endpoint (POST) to create
   short URLs.

Deployment to Fly

1. Install `flyctl` and set your `FLY_API_TOKEN`.
2. Ensure `DATABASE_URL` is configured on Fly (e.g. a managed Postgres instance).
3. Deploy (remote build):

```bash
fly deploy -a <your-app-name> --remote-only
```

Notes
- The app initializes the database engine at startup and normalizes
  `postgres://` -> `postgresql://` to avoid SQLAlchemy dialect issues.
- For production use, add alembic migrations instead of `Base.metadata.create_all`.
cd ~/aws-url-shortener

cat > README.md << 'EOF'
# LukestAWS URL Shortener – Week 1 Battle Plan (100% Complete)

**Live demo** → http://localhost:8000  
**Swagger UI** → http://localhost:8000/docs  
**Redoc** → http://localhost:8000/redoc

## Final Architecture (Week 1 – Production Grade)

```mermaid
graph LR
    A[Client] -->|8000| B(api container)
    B -->|appnet network| C(db container)
    subgraph "Docker Host"
        B[FasterAPI + Uvicorn<br/>non-root user 1001]
        C[Postgres 16-alpine<br/>persistent volume]
    end