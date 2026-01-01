
import sqlalchemy as sa
from sqlalchemy import text
import os

# Use the same connection URL (sync version)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/factoryos"

def check_schema():
    print("[*] Inspecting ams_slots schema...")
    try:
        engine = sa.create_engine(DATABASE_URL)
        with engine.connect() as conn:
            query = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'ams_slots' ORDER BY column_name")
            result = conn.execute(query)
            rows = result.fetchall()
            if not rows:
                print("!!! TABLE 'ams_slots' NOT FOUND !!!")
            else:
                print("-" * 50)
                print(f"{'COLUMN_NAME':<25} | {'DATA_TYPE':<25}")
                print("-" * 50)
                for row in rows:
                    print(f"{row[0]:<25} | {row[1]:<25}")
                print("-" * 50)
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    check_schema()
