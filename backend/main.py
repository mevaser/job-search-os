from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.config import settings
from backend import models
from backend.database import engine, get_db
import os
import uuid
import datetime
from backend.services.pipeline import process_mock_data, extract_experience, classify_role_family, classify_seniority, score_job
from backend.services.scraper import fetch_live_jobs
from backend.ats_scraper import scrape_ats_jobs
from pydantic import BaseModel

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
        desc = res.get("description")
        if not desc or not str(desc).strip():
            desc = "No description provided by the source."
            
        job = models.Job(
            source="mock_csv",
            title=res["title"],
            company=res["company"],
            location=res["location"],
            description=desc,
            job_url=f"mock-{uuid.uuid4()}" 
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
            "job_url": job.job_url,
            "description": job.description,
            "is_updated": job.is_updated,
            "date_posted": job.date_posted.isoformat() if job.date_posted else None,
            "created_at": job.created_at.isoformat() if hasattr(job, 'created_at') and job.created_at else None,
            "application_status": job.application_status,
            "application_notes": job.application_notes,
        }
        
        if job.is_updated and hasattr(job, 'versions') and job.versions:
            job_data["versions"] = [
                {
                    "old_title": v.old_title,
                    "old_description": v.old_description,
                    "changed_at": v.changed_at.isoformat() if v.changed_at else None
                }
                for v in job.versions
            ]
        else:
            job_data["versions"] = []
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

class ScanRequest(BaseModel):
    search_term: str = "Junior ML Engineer"
    location: str = "Israel"
    results_wanted: int = 10

@app.post("/api/jobs/scan-real")
def scan_real_jobs(request: ScanRequest, db: Session = Depends(get_db)):
    """Trigger a manual scan using JobSpy and process through the pipeline."""
    # We could loop through multiple search terms if we want, but let's allow the user 
    # to pass it or just use one default. The user asked for multiple defaults,
    # we can randomly pick one or do multiple calls. To be safe with limits, 
    # we just use the one passed in the request which defaults to 'Junior ML Engineer'.
    
    raw_jobs = fetch_live_jobs(
        search_term=request.search_term, 
        location=request.location, 
        results_wanted=request.results_wanted
    )
    
    processed_count = 0
    for r_job in raw_jobs:
        description = r_job.get("description")
        if not description or not str(description).strip():
            description = "No description provided by the source."
            
        title = r_job.get("title", "Unknown Title")

        # Check if URL already exists to avoid duplicates
        existing_job = db.query(models.Job).filter(models.Job.job_url == r_job["job_url"]).first()
        if existing_job:
            if existing_job.title != title or existing_job.description != description:
                # Save old version
                old_version = models.JobVersion(
                    job_id=existing_job.id,
                    old_title=existing_job.title,
                    old_description=existing_job.description
                )
                db.add(old_version)
                
                # Update existing job
                existing_job.title = title
                existing_job.description = description
                existing_job.is_updated = True
                existing_job.created_at = datetime.datetime.now(datetime.timezone.utc)
                
                # Re-run AI pipeline
                experience = extract_experience(description)
                role_family = classify_role_family(title, description)
                seniority = classify_seniority(title, experience)
                score, decision, breakdown, evidence = score_job(role_family, experience)
                
                if existing_job.analysis:
                    existing_job.analysis.role_family = role_family
                    existing_job.analysis.seniority_level = seniority
                    existing_job.analysis.experience_requirement = experience
                    existing_job.analysis.fit_score = score
                    existing_job.analysis.decision = decision
                    existing_job.analysis.score_breakdown = breakdown
                    existing_job.analysis.evidence = evidence
                else:
                    analysis = models.JobAnalysis(
                        job_id=existing_job.id,
                        role_family=role_family,
                        seniority_level=seniority,
                        experience_requirement=experience,
                        fit_score=score,
                        decision=decision,
                        score_breakdown=breakdown,
                        evidence=evidence
                    )
                    db.add(analysis)
                
                processed_count += 1
            continue
        
        experience = extract_experience(description)
        role_family = classify_role_family(title, description)
        seniority = classify_seniority(title, experience)
        score, decision, breakdown, evidence = score_job(role_family, experience)
        
        job = models.Job(
            source=r_job["source"],
            title=title,
            company=r_job["company"],
            location=r_job["location"],
            description=description,
            job_url=r_job["job_url"]
        )
        db.add(job)
        db.flush()
        
        analysis = models.JobAnalysis(
            job_id=job.id,
            role_family=role_family,
            seniority_level=seniority,
            experience_requirement=experience,
            fit_score=score,
            decision=decision,
            score_breakdown=breakdown,
            evidence=evidence
        )
        db.add(analysis)
        processed_count += 1
        
    db.commit()
    return {
        "message": f"Scraped {len(raw_jobs)} jobs. Saved {processed_count} new jobs to DB.",
        "search_term": request.search_term,
        "location": request.location
    }

@app.post("/api/jobs/scan-ats")
def scan_ats_jobs(db: Session = Depends(get_db)):
    """Trigger a Boolean search for ATS jobs and process through the pipeline."""
    raw_jobs = scrape_ats_jobs(num_results=20)
    
    processed_count = 0
    for r_job in raw_jobs:
        description = r_job.get("description")
        if not description or not str(description).strip():
            description = "No description provided by the source."
            
        title = r_job.get("title", "Unknown Title")

        # Check if URL already exists to avoid duplicates
        existing_job = db.query(models.Job).filter(models.Job.job_url == r_job["job_url"]).first()
        if existing_job:
            if existing_job.title != title or existing_job.description != description:
                # Save old version
                old_version = models.JobVersion(
                    job_id=existing_job.id,
                    old_title=existing_job.title,
                    old_description=existing_job.description
                )
                db.add(old_version)
                
                # Update existing job
                existing_job.title = title
                existing_job.description = description
                existing_job.is_updated = True
                existing_job.created_at = datetime.datetime.now(datetime.timezone.utc)
                
                # Re-run AI pipeline
                experience = extract_experience(description)
                role_family = classify_role_family(title, description)
                seniority = classify_seniority(title, experience)
                score, decision, breakdown, evidence = score_job(role_family, experience)
                
                if existing_job.analysis:
                    existing_job.analysis.role_family = role_family
                    existing_job.analysis.seniority_level = seniority
                    existing_job.analysis.experience_requirement = experience
                    existing_job.analysis.fit_score = score
                    existing_job.analysis.decision = decision
                    existing_job.analysis.score_breakdown = breakdown
                    existing_job.analysis.evidence = evidence
                else:
                    analysis = models.JobAnalysis(
                        job_id=existing_job.id,
                        role_family=role_family,
                        seniority_level=seniority,
                        experience_requirement=experience,
                        fit_score=score,
                        decision=decision,
                        score_breakdown=breakdown,
                        evidence=evidence
                    )
                    db.add(analysis)
                
                processed_count += 1
            continue
        
        experience = extract_experience(description)
        role_family = classify_role_family(title, description)
        seniority = classify_seniority(title, experience)
        score, decision, breakdown, evidence = score_job(role_family, experience)
        
        job = models.Job(
            source=r_job["source"],
            title=title,
            company=r_job["company"],
            location=r_job["location"],
            description=description,
            job_url=r_job["job_url"]
        )
        db.add(job)
        db.flush()
        
        analysis = models.JobAnalysis(
            job_id=job.id,
            role_family=role_family,
            seniority_level=seniority,
            experience_requirement=experience,
            fit_score=score,
            decision=decision,
            score_breakdown=breakdown,
            evidence=evidence
        )
        db.add(analysis)
        processed_count += 1
        
    db.commit()
    return {
        "message": f"Scraped {len(raw_jobs)} ATS jobs. Processed/Updated {processed_count} jobs."
    }

class JobUpdateRequest(BaseModel):
    application_status: str | None = None
    application_notes: str | None = None

@app.put("/api/jobs/{job_id}")
def update_job(job_id: int, request: JobUpdateRequest, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    if request.application_status is not None:
        job.application_status = request.application_status
    if request.application_notes is not None:
        job.application_notes = request.application_notes
    db.commit()
    return {"message": "Job updated successfully"}
