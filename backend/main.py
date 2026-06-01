from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend.config import settings
from backend import models
from backend.database import engine, get_db

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.app_name}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
