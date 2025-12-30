
import sqlite3
import os

db_path = "factory.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def check_table(table_name):
    print(f"\n--- Table: {table_name} ---")
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("Columns:", [c[1] for c in columns])
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error checking {table_name}: {e}")



check_table("products")
check_table("product_skus")
check_table("printers")

print("\n--- All Printers Detail ---")
cursor.execute("SELECT serial, name, ip_address, access_code FROM printers")
for row in cursor.fetchall():
    print(row)

conn.close()
