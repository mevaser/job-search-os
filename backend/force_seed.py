import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "careerflow.db")

def force_seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    company = "VastData"
    platform = "Comeet"
    url = "https://www.comeet.com/jobs/vastdata/43.001/data-engineer/2C.150"
    
    # Try inserting
    try:
        cursor.execute('''
            INSERT INTO SniperTarget (company_name, ats_platform, ats_url)
            VALUES (?, ?, ?)
        ''', (company, platform, url))
    except sqlite3.IntegrityError:
        # Update if it already exists
        cursor.execute('''
            UPDATE SniperTarget
            SET ats_platform = ?, ats_url = ?
            WHERE company_name = ?
        ''', (platform, url, company))
        
    conn.commit()
    conn.close()
    print("Force seeded VastData URL into SniperTarget.")

if __name__ == "__main__":
    force_seed()
