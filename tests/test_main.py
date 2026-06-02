import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
from backend.database import Base, get_db
from backend.models import Job

# CRITICAL: Configure the test database to use sqlite:///:memory:
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

from sqlalchemy.pool import StaticPool

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in the in-memory database
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_and_read_job():
    # Insert a mock job directly into DB
    db = TestingSessionLocal()
    mock_job = Job(
        source="linkedin",
        title="Data Engineer",
        company="AI Startup",
        location="Remote",
        url="https://linkedin.com/jobs/999",
        description="Looking for an AI engineer with Python experience."
    )
    db.add(mock_job)
    db.commit()
    db.refresh(mock_job)
    
    assert mock_job.id is not None
    
    # Read the mock job
    db_job = db.query(Job).filter(Job.id == mock_job.id).first()
    assert db_job is not None
    assert db_job.title == "Data Engineer"
    assert db_job.company == "AI Startup"
    db.close()

def test_process_mock_endpoint():
    # Make sure DB is clean before test if needed, but in-memory DB persists per sessionmaker?
    # Actually, the engine is created once, so we might have the mock_job from previous test.
    # We will just assert that processing adds new jobs and we can find them.
    response = client.post("/api/jobs/process-mock")
    assert response.status_code == 200
    data = response.json()
    assert "Successfully processed" in data["message"]
    assert "4" in data["message"] # There are 4 jobs in mock_jobs.csv

    db = TestingSessionLocal()
    from backend.models import JobAnalysis # Import here to avoid circular/top-level issues if any
    
    # Check that at least 4 jobs are now in DB with source 'mock_csv'
    jobs = db.query(Job).filter(Job.source == "mock_csv").all()
    assert len(jobs) == 4
    
    # Check that they have corresponding JobAnalysis
    for job in jobs:
        analysis = db.query(JobAnalysis).filter(JobAnalysis.job_id == job.id).first()
        assert analysis is not None
        assert analysis.decision in ["KEEP", "REVIEW", "REJECT"]
        assert job.analysis is not None # Also test relationship
    
    db.close()
