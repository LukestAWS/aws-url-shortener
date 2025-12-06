from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
import asyncio
from sqlalchemy.exc import OperationalError
import re
import base64
import tempfile
from models import Base, URLMap
import string
import random
import os


app = FastAPI(title="LukestAWS URL Shortener")

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

    # Determine SSL mode: honor explicit DB_SSL_MODE env var, keep any
    # sslmode provided in the URL, or auto-enable for Fly-hosted Postgres.
    sslmode = os.getenv("DB_SSL_MODE")
    if "sslmode=" not in (raw or ""):
        # Auto-enable SSL for Fly Postgres hosts (they contain 'flycast').
        if sslmode is None and db_url and "flycast" in db_url:
            sslmode = "require"

    # Allow providing a CA cert as a base64-encoded secret. If provided,
    # decode to a temporary file and pass `sslrootcert` to the DB driver.
    ssl_root_cert_b64 = os.getenv("DB_SSL_ROOT_CERT_BASE64")
    sslrootcert_path = None
    if ssl_root_cert_b64:
        try:
            decoded = base64.b64decode(ssl_root_cert_b64)
            tf = tempfile.NamedTemporaryFile(delete=False)
            tf.write(decoded)
            tf.flush()
            sslrootcert_path = tf.name
        except Exception as e:
            print(f"Failed to decode DB_SSL_ROOT_CERT_BASE64: {e}")

    # If sslmode is explicitly 'disable', do not pass SSL connect_args.
    connect_args = {}
    if sslmode and sslmode.lower() != "disable":
        connect_args["sslmode"] = sslmode
        if sslrootcert_path:
            connect_args["sslrootcert"] = sslrootcert_path

    # Diagnostic logging to help debug SSL EOF errors in remote logs.
    try:
        masked_url = re.sub(r"://[^@]+@", "://***@", db_url)
    except Exception:
        masked_url = db_url
    if connect_args:
        print(f"DB startup: connecting to {masked_url} with connect_args={connect_args}")
        engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    else:
        print(f"DB startup: connecting to {masked_url} with no connect_args")
        engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
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
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – healthy"}


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
    return {"short_url": f"{base_url}/r/{code}", "original": str(request.url)}


@app.get("/r/{code}")
async def redirect(code: str, db: Session = Depends(get_db)):
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    if url_map:
        raise HTTPException(status_code=307, headers={"Location": url_map.target})
    raise HTTPException(status_code=404, detail="Short code not found")