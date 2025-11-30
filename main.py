from fastapi import FastAPI
app = FastAPI(title="My AWS Portfolio – URL Shortener")
@app.get("/")
def home(): return {"message": "Welcome to my URL Shortener! Go to /docs"}
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import string
import random

app = FastAPI(title="LukestAWS URL Shortener – Week 1")

# In-memory store for Day 1 (Postgres comes tomorrow)
DB: dict[str, str] = {}

class URLRequest(BaseModel):
    url: HttpUrl

def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def root():
    return {"message": "LukestAWS URL Shortener – Day 1 running!"}

@app.post("/shorten")
async def shorten(request: URLRequest):
    code = generate_code()
    DB[code] = str(request.url)
    short_url = f"http://localhost:8000/r/{code}"
    return {"short_url": short_url, "original": request.url}

@app.get("/r/{code}")
async def redirect(code: str):
    if url := DB.get(code):
        raise HTTPException(status_code=307, headers={"Location": url})
    raise HTTPException(status_code=404, detail="Not found")
