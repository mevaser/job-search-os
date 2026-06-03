import sqlite3
import datetime

def migrate():
    conn = sqlite3.connect("jobsearchos.db")
    cursor = conn.cursor()

    try:
        # Add is_updated column to jobs table
        print("Adding is_updated column to jobs table...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN is_updated BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column is_updated already exists.")
        else:
            print(f"Error adding is_updated column: {e}")

    try:
        # Create job_versions table
        print("Creating job_versions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                old_title VARCHAR,
                old_description TEXT,
                changed_at DATETIME,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_versions_job_id ON job_versions (job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_job_versions_id ON job_versions (id)")

    except Exception as e:
        print(f"Error creating job_versions table: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
