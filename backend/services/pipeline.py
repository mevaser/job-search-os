import csv
import re
from typing import List, Dict, Any

def extract_experience(description: str) -> int:
    """Extract minimum years of experience from description."""
    pattern = r'(\d+)(?:\s*(?:-|to)\s*\d+)?(?:\+)?\s+years?'
    matches = re.findall(pattern, description.lower())
    if matches:
        return min(int(m) for m in matches)
    return 0

def classify_role_family(title: str, description: str) -> str:
    """Classify the job into a role family."""
    text = f"{title} {description}".lower()
    if "data scientist" in text:
        return "Data Science"
    if "data analyst" in text:
        return "Data Analysis"
    if "data engineer" in text:
        return "Data Engineering"
    if "python" in text and ("developer" in text or "backend" in text):
        return "Backend / Python"
    if "marketing" in text or "sales" in text:
        return "Irrelevant"
    return "Other"

def classify_seniority(title: str, experience: int) -> str:
    """Determine seniority level."""
    title_lower = title.lower()
    if "junior" in title_lower or "entry" in title_lower or experience <= 2:
        return "Junior"
    if "senior" in title_lower or "lead" in title_lower or experience >= 5:
        return "Senior"
    return "Mid"

def score_job(role_family: str, experience: int) -> tuple[float, str, str, str]:
    """Calculate fit score and decision."""
    score = 0.0
    breakdown = []
    
    if role_family in ["Data Science", "Data Analysis", "Data Engineering", "Backend / Python"]:
        score += 50.0
        breakdown.append("+50: Relevant Role Family")
    elif role_family == "Irrelevant":
        score += 0.0
        breakdown.append("+0: Irrelevant Role")
    else:
        score += 20.0
        breakdown.append("+20: Unknown/Other Role")

    if experience <= 3:
        score += 40.0
        breakdown.append(f"+40: Experience ({experience} years) is within preferred range")
    elif experience <= 5:
        score += 20.0
        breakdown.append(f"+20: Experience ({experience} years) is slightly above preferred range")
    else:
        score += 0.0
        breakdown.append(f"+0: Experience ({experience} years) is too high")
        
    decision = "REJECT"
    if score >= 80:
        decision = "KEEP"
    elif score >= 50:
        decision = "REVIEW"
        
    evidence = f"Extracted {experience} years experience. Classified as {role_family}."
    return score, decision, "\n".join(breakdown), evidence

def process_mock_data(file_path: str) -> List[Dict[str, Any]]:
    """Process the mock CSV file and run the pipeline."""
    results = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "")
            description = row.get("description", "")
            
            experience = extract_experience(description)
            role_family = classify_role_family(title, description)
            seniority = classify_seniority(title, experience)
            
            score, decision, breakdown, evidence = score_job(role_family, experience)
            
            job_analysis = {
                "title": title,
                "company": row.get("company", ""),
                "location": row.get("location", ""),
                "description": description,
                "role_family": role_family,
                "seniority_level": seniority,
                "experience_requirement": experience,
                "fit_score": score,
                "decision": decision,
                "score_breakdown": breakdown,
                "evidence": evidence
            }
            results.append(job_analysis)
            
    return results
