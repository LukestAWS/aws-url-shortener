from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import asyncio
from sqlalchemy.exc import OperationalError
from models import Base, URLMap, sessionmaker
import string
import random
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shortener:shortener@localhost:5432/shortener")
engine = None
SessionLocal = None


def _normalize_database_url(url: str) -> str:
    """Normalize common DATABASE_URL variants into SQLAlchemy-compatible schemes.

    Many platforms provide a `postgres://...` URL which SQLAlchemy no longer
    recognizes as a built-in dialect name. Convert that to `postgresql://` so
    SQLAlchemy can load the correct dialect plugin.
    """
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="LukestAWS URL Shortener – Week 1")


@app.on_event("startup")
async def startup():
    """Attempt to connect to the database with retries and create tables.

    This prevents the application from crashing at import time when the DB
    is temporarily unavailable (common during deploys).
    """
    RETRY_ATTEMPTS = 6
    RETRY_DELAY = 5  # seconds

    # Initialize the engine and sessionmaker here (not at import time). This
    # avoids import-time failures when the environment-provided DATABASE_URL
    # is temporarily invalid or uses a scheme SQLAlchemy doesn't load by
    # default (e.g. `postgres://`).
    global engine, SessionLocal
    raw_url = os.getenv("DATABASE_URL", DATABASE_URL)
    db_url = _normalize_database_url(raw_url)
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            # Lightweight connectivity check
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            # Create tables (idempotent)
            Base.metadata.create_all(bind=engine)
            break
        except OperationalError as e:
            if attempt == RETRY_ATTEMPTS:
                # Let the exception propagate so logs show the final failure
                raise
            print(f"DB connection failed (attempt {attempt}/{RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(RETRY_DELAY)

class URLRequest(BaseModel):
    url: HttpUrl

def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – LIVE on Fly.io!"}

@app.post("/shorten")
async def shorten(request: URLRequest, req: Request, db: Session = Depends(get_db)):
    # Generate a unique short code
    while True:
        code = generate_code()
        if not db.query(URLMap).filter(URLMap.code == code).first():
            break
    url_map = URLMap(code=code, target=str(request.url))
    db.add(url_map)
    db.commit()
    base_url = str(req.base_url).rstrip("/")
    return {"short_url": f"{base_url}/r/{code}", "original": request.url}

@app.get("/r/{code}")
async def redirect(code: str, db: Session = Depends(get_db)):
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    if url_map:
        raise HTTPException(status_code=307, headers={"Location": url_map.target})
    raise HTTPException(status_code=404, detail="Short code not found")