from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from models import Base, URLMap, sessionmaker
import string
import random
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shortener:shortener@localhost:5432/shortener")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LukestAWS URL Shortener – Week 1")

class URLRequest(BaseModel):
    url: HttpUrl

def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – LIVE on Fly.io!"}

@app.post("/shorten")
async def shorten(request: URLRequest, req: Request):
    db: Session = SessionLocal()
    while True:
        code = generate_code()
        if not db.query(URLMap).filter(URLMap.code == code).first():
            break
    url_map = URLMap(code=code, target=str(request.url))
    db.add(url_map)
    db.commit()
    db.close()
    base_url = str(req.base_url).rstrip("/")
    return {"short_url": f"{base_url}/r/{code}", "original": request.url}

@app.get("/r/{code}")
async def redirect(code: str):
    db: Session = SessionLocal()
    url_map = db.query(URLMap).filter(URLMap.code == code).first()
    db.close()
    if url_map:
        raise HTTPException(status_code=307, headers={"Location": url_map.target})
    raise HTTPException(status_code=404, detail="Short code not found")