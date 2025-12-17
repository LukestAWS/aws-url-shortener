import redis # Still needed for REDIS_TTL constant
import os
import asyncio
import string
import secrets
from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, IntegrityError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# --- Import Caching Functions ---
# Import the functions defined in the provided cache.py
from cache import get_long_from_cache, get_short_from_cache, set_cache

# --- Application-specific Imports (Assuming they exist) ---
from models import Base, URLMap # Assuming URLMap is defined here

# --- Redis Configuration ---
# NOTE: The redis_client object is still needed here for access to REDIS_TTL
# The client itself is now managed within cache.py, but we keep the constant.
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)  # 24h

app = FastAPI()
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)  # docker-compose service name


# --- FastAPI Initialization ---
app = FastAPI(title="LukestAWS URL Shortener")

# Deploy marker to help confirm which `main.py` is running in deployed image
print("DEPLOY_MARKER: restored-main-20251215-02") # Updated marker

# --- Configuration ---
DEFAULT_DATABASE_URL = "postgresql://shortener:shortener@localhost:5432/shortener"
RETRY_ATTEMPTS = int(os.getenv("DB_RETRY_ATTEMPTS", "6"))
RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", "5"))

engine = None
SessionLocal = None


def _normalize_database_url(url: str) -> str:
    """Normalize 'postgres://' to 'postgresql://' for SQLAlchemy."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_db():
    """Dependency to yield a new database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/shorten")
async def shorten(url: str):
    # Check cache first
    cached = r.get(url)
    if cached:
        return {"short": cached, "cached": True}
    
    # Generate short code (your logic)
    short_code = generate_short_code(url)  # your function
    
    # Cache it
    r.set(url, short_code, ex=86400)  # 24h TTL
    r.set(short_code, url, ex=86400)   # for redirect lookup
    
    # Save to Postgres too (your existing logic)
    
    return {"short": short_code}
docker-compose.yml

@app.on_event("startup")
async def startup():
    """Initialize DB engine and create tables after successful connection."""
    global engine, SessionLocal
    raw = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    db_url = _normalize_database_url(raw)

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # --- TEMPORARY FIX: CREATE TABLES ---
            # This ensures the 'url_map' table is present on startup.
            #Base.metadata.create_all(bind=engine)
            # -----------------------------------

            print("DB connection successful.")
            break
        except OperationalError as e:
            if attempt == RETRY_ATTEMPTS:
                print("DB connection failed permanently.")
                raise
            print(f"DB connection failed (attempt {attempt}/{RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(RETRY_DELAY)


# --- Schemas ---
class URLRequest(BaseModel):
    url: HttpUrl


# --- Utility Functions ---
def generate_code(length: int = 6) -> str:
    """Generate a cryptographically strong random short code."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# --- Database Operations (Used by shorten) ---

def create_or_get_short_code(db: Session, long_url: str) -> str:
    """
    Tries to find an existing code for the long_url, or creates a new one.
    Handles collision by retrying code generation.
    """
    # 1. Check if URL already exists
    existing_map = db.query(URLMap).filter(URLMap.target == long_url).first()
    if existing_map:
        return existing_map.code

    # 2. Create new code with retry logic
    for _ in range(5):  # Try 5 times
        code = generate_code()
        url_map = URLMap(code=code, target=long_url)
        try:
            db.add(url_map)
            db.commit()
            return code
        except IntegrityError:
            db.rollback()
            continue
    
    raise HTTPException(status_code=500, detail="Could not generate unique code, please try again")


def get_long_url_from_db(db: Session, code: str) -> str | None:
    """Retrieve the target URL from the database using the short code."""
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    return url_map.target if url_map else None


# --- Authentication ---
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verifies the API key provided in the Authorization header."""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="Server configuration error: API_KEY not set")
    
    if credentials.credentials != expected_key:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return credentials.credentials


# --- Routes ---

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

    # 1. Cache check (long_url -> code)
    cached_code = get_short_from_cache(long_url)
    if cached_code:
        base_url = str(req.base_url).rstrip("/")
        return {"short_url": f"{base_url}/r/{cached_code}", "original": long_url}

    # 2. DB create/get logic
    short_code = create_or_get_short_code(db, long_url)

    # 3. Cache both directions
    set_cache(short_code, long_url)

    base_url = str(req.base_url).rstrip("/")
    return {"short_url": f"{base_url}/r/{short_code}", "original": long_url}


@app.get("/r/{code}")
async def redirect(code: str, db: Session = Depends(get_db)):
    # 1. Cache check (code -> long_url)
    cached_url = get_long_from_cache(code)
    if cached_url:
        return RedirectResponse(cached_url, status_code=307)

    # 2. DB fallback
    long_url = get_long_url_from_db(db, code)
    if not long_url:
        raise HTTPException(status_code=404, detail="Short code not found")

    # 3. Cache it (both directions)
    set_cache(code, long_url)

    return RedirectResponse(long_url, status_code=307)