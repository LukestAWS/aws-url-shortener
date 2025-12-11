from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
import asyncio
from sqlalchemy.exc import OperationalError
from models import Base, URLMap
import string
import random
import secrets
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from sqlalchemy.exc import IntegrityError


app = FastAPI(title="LukestAWS URL Shortener")

# Deploy marker to help confirm which `main.py` is running in deployed image
print("DEPLOY_MARKER: restored-main-20251206-01")

# Configuration
DEFAULT_DATABASE_URL = "postgresql://shortener:shortener@localhost:5432/shortener"
RETRY_ATTEMPTS = int(os.getenv("DB_RETRY_ATTEMPTS", "6"))
RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", "5"))

engine = None
SessionLocal = None


def _normalize_database_url(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    """Initialize DB engine and create tables after successful connection.

    This keeps import-time lightweight and avoids crashes when DATABASE_URL
    is temporarily invalid or the network is slow during deploys.
    """
    global engine, SessionLocal
    raw = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    db_url = _normalize_database_url(raw)

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Base.metadata.create_all(bind=engine)  # Replaced by Alembic
            app.logger = getattr(app, "logger", None)
            break
        except OperationalError as e:
            if attempt == RETRY_ATTEMPTS:
                raise
            print(f"DB connection failed (attempt {attempt}/{RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(RETRY_DELAY)


class URLRequest(BaseModel):
    url: HttpUrl


def generate_code(length: int = 6) -> str:
    # Use secrets for cryptographically strong random selection
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – healthy"}


security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        # Fail safe if API_KEY is not configured
        raise HTTPException(status_code=500, detail="Server configuration error: API_KEY not set")
    
    if credentials.credentials != expected_key:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return credentials.credentials


@app.post("/shorten")
async def shorten(
    request: URLRequest, 
    req: Request, 
    db: Session = Depends(get_db), 
    _: str = Depends(verify_api_key)
):
    # Generate a unique short code with retry on race condition
    for _ in range(5):  # Try 5 times
        code = generate_code()
        # Optimistic: try to insert directly
        url_map = URLMap(code=code, target=str(request.url))
        try:
            db.add(url_map)
            db.commit()
            break
        except IntegrityError:
            db.rollback()
            continue
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique code, please try again")

    base_url = str(req.base_url).rstrip("/")
    return {"short_url": f"{base_url}/r/{code}", "original": str(request.url)}


@app.get("/r/{code}")
async def redirect(code: str, db: Session = Depends(get_db)):
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    if url_map:
        raise HTTPException(status_code=307, headers={"Location": url_map.target})
    raise HTTPException(status_code=404, detail="Short code not found")