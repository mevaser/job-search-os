import sqlite3
import datetime

conn = sqlite3.connect('jobsearchos.db')
cursor = conn.cursor()

# שליפת המשרה הראשונה
cursor.execute("SELECT id, title, description FROM jobs LIMIT 1")
job = cursor.fetchone()

if job:
    job_id, old_title, old_desc = job
    now = datetime.datetime.utcnow().isoformat()
    
    # הכנסת הגרסה הנוכחית לטבלת ההיסטוריה
    cursor.execute("""
        INSERT INTO job_versions (job_id, old_title, old_description, changed_at)
        VALUES (?, ?, ?, ?)
    """, (job_id, old_title, old_desc, now))
    
    # עדכון המשרה הראשית והדלקת דגל העדכון
    cursor.execute("""
        UPDATE jobs 
        SET title = title || ' (TEST UPDATE)', 
            is_updated = 1 
        WHERE id = ?
    """, (job_id,))
    
    conn.commit()
    print("Success: Version history created and job updated.")
else:
    print("No jobs found in the database.")

conn.close()