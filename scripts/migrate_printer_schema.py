import sqlite3
import os

DB_PATH = "factory.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("factory.db not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(printers)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "current_job_id" in columns:
        print("✅ Column 'current_job_id' already exists in 'printers'.")
    else:
        print("⚠️ Column 'current_job_id' missing. Adding it...")
        try:
            cursor.execute("ALTER TABLE printers ADD COLUMN current_job_id INTEGER")
            conn.commit()
            print("✅ Migration successful: Added 'current_job_id' to 'printers'.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            
    conn.close()

if __name__ == "__main__":
    migrate()
