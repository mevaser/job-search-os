import os
import sqlite3
import json
import logging
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY is not set in the environment.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Define Primary and Fallback Models
PRIMARY_MODEL_NAME = 'gemini-3.5-pro'
FALLBACK_MODEL_NAME = 'gemini-3.5-flash'

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "careerflow.db")

# LLM Filtering Criteria (System Prompt)
SYSTEM_PROMPT = """
You are an expert technical recruiter and job evaluator.
Your task is to analyze the provided job description and determine its fit for our candidate.

Target Roles:
- AI Engineer
- Data Analyst
- Data Science
- Python Developer
- Backend Development
- Data Engineering
- Big Data
- AND any other adjacent/hybrid technical roles that fit this ecosystem.

You must respond strictly in JSON format with the following three fields:
- "score": An integer from 0 to 100 representing how well the role fits the target criteria.
- "job_title": A string with the extracted job title from the description.
- "reason": A brief explanation of why it received this specific score.
"""

def extract_job_text(url: str) -> str:
    """Scrape the given ATS URL and extract visible text."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        # Limit text length to avoid exceeding context window unexpectedly
        return text[:15000] 
    except Exception as e:
        logging.error(f"Failed to scrape {url}: {e}")
        return ""

def evaluate_job_with_llm(job_text: str) -> dict:
    """Evaluate the job text using the primary LLM, with a fallback to a weaker model."""
    if not job_text.strip():
        return {"score": 0, "job_title": "Unknown Title", "reason": "Empty job description."}

    prompt = f"{SYSTEM_PROMPT}\n\nJob Description:\n{job_text}"
    
    # Try Primary Model
    try:
        logging.info(f"Attempting evaluation with Primary Model ({PRIMARY_MODEL_NAME})...")
        model = genai.GenerativeModel(PRIMARY_MODEL_NAME, generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str or "deprecat" in error_str:
            logging.warning(f"Primary model unavailable (quota/rate-limit/deprecated). Falling back to {FALLBACK_MODEL_NAME}... Error: {e}")
        else:
            logging.warning(f"Primary model failed due to unexpected error: {e}. Falling back to {FALLBACK_MODEL_NAME}...")
        
    # Try Fallback Model
    try:
        logging.info(f"Attempting evaluation with Fallback Model ({FALLBACK_MODEL_NAME})...")
        model = genai.GenerativeModel(FALLBACK_MODEL_NAME, generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        logging.error(f"Fallback model also failed: {e}")
        return {"score": 0, "job_title": "Unknown Title", "reason": f"Evaluation failed due to LLM error: {e}"}

def process_targets():
    """Iterate through the SniperTarget table and process each URL."""
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch targets from the staging database
    try:
        cursor.execute("SELECT id, company_name, ats_url FROM SniperTarget WHERE ats_url IS NOT NULL")
        targets = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logging.error(f"Could not read from SniperTarget: {e}")
        conn.close()
        return
    
    if not targets:
        logging.info("No targets found in SniperTarget table.")
        conn.close()
        return

    logging.info(f"Found {len(targets)} targets to process.")
    
    for target in targets:
        target_id = target['id']
        company = target['company_name']
        url = target['ats_url']
        
        logging.info(f"\n--- Processing Target [{target_id}] {company} ---")
        logging.info(f"URL: {url}")
        
        job_text = extract_job_text(url)
        if not job_text:
            logging.info("Skipping evaluation due to missing text.")
            continue
            
        evaluation = evaluate_job_with_llm(job_text)
        
        score = evaluation.get("score", 0)
        reason = evaluation.get("reason", "No reason provided.")
        job_title = evaluation.get("job_title", "Unknown Title")
        
        logging.info(f"Score: {score}")
        logging.info(f"Reason: {reason}")
        logging.info(f"Job Title: {job_title}")
        
        cursor.execute('''
            INSERT INTO MatchedJobs (company_name, job_title, job_url, match_reason, match_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (company, job_title, url, reason, score))
        conn.commit()
        logging.info(f"Saved job to MatchedJobs table with score {score}.")
        
        # Small delay to be polite to the target servers and LLM APIs
        time.sleep(2)

    conn.close()
    logging.info("Finished processing all targets.")

if __name__ == "__main__":
    process_targets()
