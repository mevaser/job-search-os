import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'jobsearchos.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "application_status" not in columns:
        print("Adding application_status column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN application_status VARCHAR DEFAULT 'Not Applied'")
        
    if "application_notes" not in columns:
        print("Adding application_notes column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN application_notes TEXT DEFAULT ''")
        
    conn.commit()
    print("CRM migration successful.")
except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()
