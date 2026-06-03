import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'jobsearchos.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "job_url" not in columns:
        print("Adding job_url column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN job_url VARCHAR")
        
        # Migrate data from url to job_url
        if "url" in columns:
            print("Migrating data from url to job_url...")
            cursor.execute("UPDATE jobs SET job_url = url")
            
        conn.commit()
        print("Migration successful.")
    else:
        print("Column job_url already exists.")
except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()
