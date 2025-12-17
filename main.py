import os
import secrets
import string
from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session  # ← ADD Session here
from sqlalchemy.exc import OperationalError, IntegrityError

# --- Cache Functions ---
from cache import get_long_from_cache, get_short_from_cache, set_cache

# --- Models ---
from models import Base, URLMap

# --- Config ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shortener:shortener@db:5432/shortener")
API_KEY = os.getenv("API_KEY")

# --- DB Engine ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth ---
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# --- Pydantic Model ---
class URLRequest(BaseModel):
    url: HttpUrl

# --- Helper ---
def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

# --- App ---
app = FastAPI(title="LukestAWS URL Shortener")

print("DEPLOY_MARKER: final-main-redis-caching-20251217")

@app.on_event("startup")
async def startup():
    # Create tables on startup (safe when DB ready)
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – healthy"}

@app.post("/shorten")
async def shorten(
    request: URLRequest,
    req: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    long_url = str(request.url).rstrip("/")

    # CACHE HIT?
    cached_code = get_short_from_cache(long_url)
    if cached_code:
        base_url = str(req.base_url).rstrip("/")
        return {
            "short_url": f"{base_url}/r/{cached_code}",
            "original": long_url,
            "cached": True,
            "message": "Cache hit – served from Redis!"
        }

    # DB logic
    existing = db.query(URLMap).filter(URLMap.target == long_url).first()
    if existing:
        short_code = existing.code
    else:
        for _ in range(5):
            short_code = generate_code()
            try:
                db.add(URLMap(code=short_code, target=long_url))
                db.commit()
                break
            except IntegrityError:
                db.rollback()
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique code")

    # CACHE BOTH DIRECTIONS
    set_cache(long_url, short_code)
    set_cache(short_code, long_url)

    base_url = str(req.base_url).rstrip("/")
    return {
        "short_url": f"{base_url}/r/{short_code}",
        "original": long_url,
        "cached": False,
        "message": "New URL created + cached in Redis"
    }

@app.get("/r/{code}")
async def redirect(code: str, req: Request, db: Session = Depends(get_db)):
    # CACHE HIT?
    cached_url = get_long_from_cache(code)
    if cached_url:
        return RedirectResponse(cached_url, status_code=307)

    # DB fallback
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    if not url_map:
        raise HTTPException(status_code=404, detail="Short code not found")

    # CACHE IT
    set_cache(code, url_map.target)
    set_cache(url_map.target, code)

    return RedirectResponse(url_map.target, status_code=307)