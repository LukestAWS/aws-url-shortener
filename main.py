from fastapi import FastAPI
app = FastAPI(title="My AWS Portfolio – URL Shortener")
@app.get("/")
def home(): return {"message": "Welcome to my URL Shortener! Go to /docs"}
