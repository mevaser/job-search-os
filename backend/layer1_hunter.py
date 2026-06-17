import os
import sqlite3
import json
import logging
import feedparser
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Initialize Firebase Admin
FIREBASE_SERVICE_ACCOUNT_KEY = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
db_firestore = None
if FIREBASE_SERVICE_ACCOUNT_KEY:
    try:
        service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY)
        cred = credentials.Certificate(service_account_info)
        # Avoid double initialization if called in a shared context
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db_firestore = firestore.client()
        logging.info("Firebase initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Firebase: {e}")
else:
    logging.warning("FIREBASE_SERVICE_ACCOUNT_KEY not found in environment. Firebase pushes will be disabled.")

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "careerflow.db")

# Target keywords
TARGET_KEYWORDS = ["data", "python", "junior", "analyst", "engineer", "ai"]

# Placeholder RSS Feeds for tech job boards
RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-data-programming-jobs.rss",
    "https://remoteok.com/remote-data-jobs.rss",
    "https://hnrss.org/jobs"
]

def check_if_exists_in_sqlite(url: str) -> bool:
    """Check if the job URL already exists in the local SQLite MatchedJobs database."""
    if not os.path.exists(DB_PATH):
        return False
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM MatchedJobs WHERE job_url = ?", (url,))
        result = cursor.fetchone()
        conn.close()
        return bool(result)
    except sqlite3.OperationalError:
        return False

def check_if_exists_in_firestore(url: str) -> bool:
    """Check if the job URL already exists in Firestore to prevent double pending."""
    if not db_firestore:
        return False
        
    try:
        docs = db_firestore.collection('jobs').where('job_url', '==', url).limit(1).get()
        return len(docs) > 0
    except Exception as e:
        logging.error(f"Failed to check Firestore: {e}")
        return False

def hunt_for_jobs():
    if not db_firestore:
        logging.error("Cannot hunt for jobs without Firestore connection. Exiting.")
        return

    logging.info("Starting Layer 1: Auto Hunter...")
    
    new_jobs_found = 0
    
    for feed_url in RSS_FEEDS:
        logging.info(f"Parsing RSS Feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logging.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
            continue
            
        for entry in feed.entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            link = entry.get('link', '')
            
            if not link:
                continue
                
            combined_text = f"{title} {summary}".lower()
            
            if any(keyword in combined_text for keyword in TARGET_KEYWORDS):
                
                if check_if_exists_in_sqlite(link):
                    continue
                    
                if check_if_exists_in_firestore(link):
                    continue
                    
                logging.info(f"Hunter found new job match: {title} - {link}")
                
                try:
                    doc_ref = db_firestore.collection('jobs').document()
                    doc_ref.set({
                        'job_url': link,
                        'status': 'pending',
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'source': 'auto_hunter'
                    })
                    logging.info(f"Pushed to Firestore with status pending.")
                    new_jobs_found += 1
                except Exception as e:
                    logging.error(f"Failed to push {link} to Firestore: {e}")
                    
    logging.info(f"Layer 1 Hunter completed. Found {new_jobs_found} new jobs.")

if __name__ == "__main__":
    hunt_for_jobs()
