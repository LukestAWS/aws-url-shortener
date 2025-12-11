# LukestAWS URL Shortener 🚀

Production-grade URL shortener built with FastAPI, Postgres, Alembic migrations, and Docker.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-https://aws-url-shortener.fly.dev-brightgreen)](https://aws-url-shortener.fly.dev)

## Public Demo
- Health check: https://aws-url-shortener.fly.dev → {"message":"LukestAWS URL Shortener – healthy"}
- Shorten: `POST https://aws-url-shortener.fly.dev/shorten` with JSON {"url": "your-long-url"}
- Example short URL: https://aws-url-shortener.fly.dev/r/nbZOl4 → redirects correctly
- Swagger UI: https://aws-url-shortener.fly.dev/docs
- Redoc: https://aws-url-shortener.fly.dev/redoc

## Tech Stack
- FastAPI backend
- PostgreSQL + Alembic migrations
- Docker Compose local dev
- Multi-stage Dockerfile
- Deployed on Fly.io (free tier)

Week 1–2 of 20-week AWS portfolio battle plan – Docker Fundamentals **COMPLETE** ✅

## Final Architecture (Week 1 – Production Grade)
```mermaid
graph LR
    A[Client] -->|8000| B(api container)
    B -->|appnet network| C(db container)
    subgraph "Docker Host (Local) / Fly.io (Prod)"
        B[FastAPI + Uvicorn<br/>non-root user 1001<br/>Multi-stage build]
        C[Postgres 16-alpine<br/>persistent volume<br/>SSL required in prod]
    end


## Local Demo (for development)
- **Live demo (local)** → http://localhost:8000
- **Swagger UI** → http://localhost:8000/docs
- **Redoc** → http://localhost:8000/redoc

## Quick start (local)
1. Build and run with Docker Compose:
```bash
docker compose up --build

## Deployment to Fly
1. Install `flyctl` and set your `FLY_API_TOKEN`.
2. Ensure `DATABASE_URL` is configured on Fly (e.g. a managed Postgres instance with `?sslmode=require`).
3. Deploy (remote build):
```bash
fly deploy --remote-only
