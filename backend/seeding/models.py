import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "careerflow.db")

def init_db():
    """Initializes the SQLite database with the necessary tables."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Staging area for Layer 1 & 2
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PendingVerification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            raw_url TEXT,
            source TEXT, -- 'email', 'rss'
            status TEXT DEFAULT 'pending' -- 'pending', 'verified', 'failed'
        )
    ''')
    
    # The Sniper Database
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SniperTarget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE,
            ats_platform TEXT,
            ats_url TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Matched Jobs Database
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MatchedJobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            job_title TEXT,
            job_url TEXT,
            match_reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_pending_company(company_name: str, raw_url: str, source: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO PendingVerification (company_name, raw_url, source)
        VALUES (?, ?, ?)
    ''', (company_name, raw_url, source))
    conn.commit()
    conn.close()

def add_sniper_target(company_name: str, ats_platform: str, ats_url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO SniperTarget (company_name, ats_platform, ats_url)
            VALUES (?, ?, ?)
        ''', (company_name, ats_platform, ats_url))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
