import os
import sqlite3
import json
import logging
import re
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from telethon import TelegramClient, events

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

TELEGRAM_API_ID = os.environ.get("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")

if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
    logging.error("Telegram API credentials not found in .env. Please configure TELEGRAM_API_ID and TELEGRAM_API_HASH.")
    exit(1)

# Initialize Firebase Admin
FIREBASE_SERVICE_ACCOUNT_KEY = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
db_firestore = None
if FIREBASE_SERVICE_ACCOUNT_KEY:
    try:
        service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY)
        cred = credentials.Certificate(service_account_info)
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

# Configurable list of target chats
TARGET_CHATS = ['Secret Hunter', 'משרות הייטק ושכר ללא ניסיון']

# URL regex
URL_REGEX = r'(https?://[^\s]+)'

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

# Initialize the Telegram Client
client = TelegramClient('local_radar_session', int(TELEGRAM_API_ID), TELEGRAM_API_HASH)

@client.on(events.NewMessage(chats=TARGET_CHATS))
async def new_message_listener(event):
    message_text = event.message.message or ""
    
    # 1. Extract URLs from the message using regex
    urls = re.findall(URL_REGEX, message_text)
    
    # Alternatively, use telethon entities if they exist
    if event.message.entities:
        for ent in event.message.entities:
            if hasattr(ent, 'url') and ent.url:
                urls.append(ent.url)
    
    urls = list(set(urls))  # Deduplicate
    
    if not urls:
        return
        
    # 2. Check for keywords
    text_lower = message_text.lower()
    if not any(keyword in text_lower for keyword in TARGET_KEYWORDS):
        return
        
    logging.info(f"Found matching message with {len(urls)} URLs in chat {event.chat_id}")
    
    # 3. Process URLs
    for url in urls:
        if check_if_exists_in_sqlite(url):
            logging.info(f"URL already exists in SQLite: {url}")
            continue
            
        if check_if_exists_in_firestore(url):
            logging.info(f"URL already exists in Firestore: {url}")
            continue
            
        logging.info(f"Telegram Listener found new job match: {url}")
        
        # 4. Push to Firestore
        if db_firestore:
            try:
                doc_ref = db_firestore.collection('jobs').document()
                doc_ref.set({
                    'job_url': url,
                    'status': 'pending',
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'source': 'telegram'
                })
                logging.info(f"Pushed to Firestore with status pending.")
            except Exception as e:
                logging.error(f"Failed to push {url} to Firestore: {e}")

if __name__ == '__main__':
    logging.info("Starting Layer 2: Telegram Listener...")
    client.start()
    logging.info("Listening for new messages...")
    client.run_until_disconnected()
