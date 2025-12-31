import sqlite3
import pandas as pd

def dump_slots():
    conn = sqlite3.connect("factory.db")
    try:
        df = pd.read_sql_query("SELECT * FROM ams_slots", conn)
        print(df)
    except Exception as e:
        print(f"Error: {e}")
        # List tables to be sure
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print("Tables:", cursor.fetchall())
    finally:
        conn.close()

if __name__ == "__main__":
    dump_slots()
