from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

# Use in-memory SQLite for testing to avoid locking
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Mock fetch_live_jobs
import backend.main
def mock_fetch_live_jobs(search_term, location, results_wanted):
    return [
        {
            "title": "Junior Python Developer",
            "company": "TestCorp",
            "location": location,
            "description": "Looking for a Python dev with 1 year experience.",
            "url": "http://test-url.com/1",
            "source": "jobspy_test"
        }
    ]

backend.main.fetch_live_jobs = mock_fetch_live_jobs

def test_scan_real_jobs():
    response = client.post("/api/jobs/scan-real", json={
        "search_term": "Junior Python",
        "location": "Israel",
        "results_wanted": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert "Scraped 1 jobs" in data["message"]
    
    # Verify DB insertion
    db = TestingSessionLocal()
    from backend.models import Job, JobAnalysis
    jobs = db.query(Job).all()
    assert len(jobs) == 1
    assert jobs[0].title == "Junior Python Developer"
    
    analysis = db.query(JobAnalysis).first()
    assert analysis is not None
    assert analysis.experience_requirement == 1
    assert analysis.role_family == "Backend / Python"
    
    db.close()
