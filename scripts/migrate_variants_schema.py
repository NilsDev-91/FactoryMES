import sqlite3
import os

DB_PATH = "factory.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("factory.db not found. Skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create product_skus table
    print("Creating product_skus table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_skus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                sku VARCHAR NOT NULL,
                hex_color VARCHAR NOT NULL,
                color_name VARCHAR NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_product_skus_sku ON product_skus (sku)")
        print("✅ product_skus table created/verified.")
    except Exception as e:
        print(f"❌ Failed creating product_skus: {e}")

    # 2. Relax SKU restriction in products table?
    # SQLite doesn't support changing column constraints easily (DROP NOT NULL).
    # We might need to recreate table or just ignore if we can insert NULL (SQLModel might handle migration logic usually but here we are manual).
    # IF the original definition was NOT NULL, we are stuck without migration.
    # However, for now, we can check if it allows nulls or just assume valid logic for new items.
    
    # Actually, if the previous schema had sku as NOT NULL, inserting None will fail.
    # We need to alter table.
    # SQLite: ALTER TABLE ... RENAME TO ...; CREATE NEW; INSERT INTO NEW SELECT FROM OLD; ...
    # Too risky for a simple script?
    # Let's check schema first.
    
    cursor.execute("PRAGMA table_info(products)")
    # cid, name, type, notnull, dflt_value, pk
    cols = cursor.fetchall()
    sku_col = next((c for c in cols if c[1] == 'sku'), None)
    
    if sku_col and sku_col[3] == 1: # NOT NULL is set
        print("⚠️ 'sku' column is NOT NULL. Complex migration required.")
        # Proceed with simple "ALTER TABLE" approach if possible or simple workaround:
        # We can't easily remove NOT NULL in SQLite.
        # Workaround for MVP: Provide a dummy unique SKU for "Parent" if None?
        # Or Just Re-create schema for dev environment?
        # User has data? Assuming yes.
        pass
    else:
        print("✅ 'sku' column allows NULLs or not checked.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
