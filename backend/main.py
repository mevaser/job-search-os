from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(models.Job).all()
    # We will just return a simple list of dicts for now to avoid setting up complex Pydantic schemas right away
    result = []
    for job in jobs:
        job_data = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "source": job.source,
            "url": job.url,
            "date_posted": job.date_posted.isoformat() if job.date_posted else None,
        }
        if job.analysis:
            job_data["analysis"] = {
                "role_family": job.analysis.role_family,
                "seniority_level": job.analysis.seniority_level,
                "experience_requirement": job.analysis.experience_requirement,
                "fit_score": job.analysis.fit_score,
                "decision": job.analysis.decision,
                "score_breakdown": job.analysis.score_breakdown,
                "evidence": job.analysis.evidence,
            }
        else:
            job_data["analysis"] = None
        result.append(job_data)
        
    return result
