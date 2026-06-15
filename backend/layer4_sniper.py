import os
import sqlite3
import json
import logging
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

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

# Initialize Firebase Admin
FIREBASE_SERVICE_ACCOUNT_KEY = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
db_firestore = None
if FIREBASE_SERVICE_ACCOUNT_KEY:
    try:
        service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY)
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        db_firestore = firestore.client()
        logging.info("Firebase initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Firebase: {e}")
else:
    logging.warning("FIREBASE_SERVICE_ACCOUNT_KEY not found in environment. Firebase pushes will be disabled.")

# Define Primary and Fallback Models
PRIMARY_MODEL_NAME = 'gemini-2.5-pro'
FALLBACK_MODEL_NAME = 'gemini-2.5-flash'

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
    """Scrape the given ATS URL and extract visible text using Jina Reader API with a fallback to Playwright for SPAs."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    text = ""
    # Primary: Jina Reader API
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, headers=headers, timeout=20)
        response.raise_for_status()
        text = response.text.strip()
        print(f"DEBUG: Scraped {len(text)} characters from {url} (Jina)")
    except Exception as e:
        logging.warning(f"Jina extraction failed for {url}: {e}")

    # Fallback: BeautifulSoup if Jina failed
    if not text or len(text) <= 100:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            print(f"DEBUG: Scraped {len(text)} characters from {url} (BeautifulSoup)")
        except Exception as e:
            logging.error(f"Failed to scrape {url} with BeautifulSoup: {e}")
            text = ""

    # Validation check for False Negatives (SPAs like Comeet/Greenhouse)
    false_negative_phrases = [
        "no open positions",
        "no job openings at the moment",
        "we're sorry",
        "we are sorry",
        "javascript is required",
        "enable javascript",
        "please enable js"
    ]
    
    is_suspicious = False
    if len(text) < 300:
        is_suspicious = True
        
    text_lower = text.lower()
    for phrase in false_negative_phrases:
        if phrase in text_lower:
            is_suspicious = True
            break
            
    if is_suspicious:
        logging.warning(f"Scraped text for {url} is suspicious. Triggering Playwright fallback.")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Wait a bit for JS to render
                page.wait_for_timeout(3000)
                text = page.evaluate("document.body.innerText")
                browser.close()
                text = text.strip() if text else ""
                print(f"DEBUG: Scraped {len(text)} characters from {url} (Playwright)")
        except Exception as e:
            logging.error(f"Playwright fallback failed for {url}: {e}")

    return text[:15000] if text else ""

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
        
        job_description = job_text[:3000]
        
        cursor.execute('''
            INSERT INTO MatchedJobs (company_name, job_title, job_url, match_reason, match_score, job_description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (company, job_title, url, reason, score, job_description))
        conn.commit()
        logging.info(f"Saved job to MatchedJobs table with score {score}.")
        
        # Push to Firebase
        if db_firestore:
            try:
                doc_ref = db_firestore.collection('jobs').document()
                doc_ref.set({
                    'job_title': job_title,
                    'company_name': company,
                    'job_url': url,
                    'match_score': score,
                    'match_reason': reason,
                    'job_description': job_description,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
                logging.info("Pushed job to Firestore.")
            except Exception as e:
                logging.error(f"Failed to push job to Firestore: {e}")
        
        # Small delay to be polite to the target servers and LLM APIs
        time.sleep(2)

    conn.close()
    logging.info("Finished processing all targets.")

if __name__ == "__main__":
    process_targets()
