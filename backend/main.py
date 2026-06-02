from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend.config import settings
from backend import models
from backend.database import engine, get_db
import os
import uuid
from backend.services.pipeline import process_mock_data
# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.app_name}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/jobs/process-mock")
def process_mock_jobs(db: Session = Depends(get_db)):
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "mock_jobs.csv")
    results = process_mock_data(file_path)
    
    processed_count = 0
    for res in results:
        job = models.Job(
            source="mock_csv",
            title=res["title"],
            company=res["company"],
            location=res["location"],
            description=res.get("description", ""),
            url=f"mock-{uuid.uuid4()}" 
        )
        db.add(job)
        db.flush() 
        
        analysis = models.JobAnalysis(
            job_id=job.id,
            role_family=res["role_family"],
            seniority_level=res["seniority_level"],
            experience_requirement=res["experience_requirement"],
            fit_score=res["fit_score"],
            decision=res["decision"],
            score_breakdown=res["score_breakdown"],
            evidence=res["evidence"]
        )
        db.add(analysis)
        processed_count += 1
        
    db.commit()
    return {"message": f"Successfully processed {processed_count} jobs from mock data."}
