
import sqlite3
import os

def check_wal():
    if not os.path.exists('factory.db'):
        print("factory.db not found!")
        return

    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode;')
    mode = cursor.fetchone()[0]
    print(f"Journal Mode: {mode}")
    if mode.lower() == 'wal':
        print("SUCCESS: Database is in WAL mode.")
    else:
        print(f"FAILURE: Database is in {mode} mode, expected WAL.")
    conn.close()

if __name__ == "__main__":
    check_wal()
