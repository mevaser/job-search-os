import os
import pytest
from backend.services.pipeline import process_mock_data

def test_pipeline_on_mock_data():
    # Construct path to mock data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mock_file_path = os.path.join(current_dir, '..', 'data', 'mock_jobs.csv')
    
    # Run the pipeline
    results = process_mock_data(mock_file_path)
    
    assert len(results) == 4
    
    # 1. Junior Data Analyst
    job_1 = next(j for j in results if j["title"] == "Junior Data Analyst")
    assert job_1["experience_requirement"] == 1
    assert job_1["role_family"] == "Data Analysis"
    assert job_1["seniority_level"] == "Junior"
    assert job_1["fit_score"] == 90.0
    assert job_1["decision"] == "KEEP"
    
    # 2. Senior Data Scientist
    job_2 = next(j for j in results if j["title"] == "Senior Data Scientist")
    assert job_2["experience_requirement"] == 5
    assert job_2["role_family"] == "Data Science"
    assert job_2["seniority_level"] == "Senior"
    assert job_2["fit_score"] == 70.0
    assert job_2["decision"] == "REVIEW"
    
    # 3. Marketing Manager
    job_3 = next(j for j in results if j["title"] == "Marketing Manager")
    assert job_3["experience_requirement"] == 3
    assert job_3["role_family"] == "Irrelevant"
    assert job_3["fit_score"] == 40.0
    assert job_3["decision"] == "REJECT"

    # 4. Python Backend Developer
    job_4 = next(j for j in results if j["title"] == "Python Backend Developer")
    assert job_4["experience_requirement"] == 2
    assert job_4["role_family"] == "Backend / Python"
    assert job_4["fit_score"] == 90.0
    assert job_4["decision"] == "KEEP"
