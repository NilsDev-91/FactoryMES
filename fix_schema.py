
import asyncio
import sys
from sqlalchemy import text
from database import engine

async def fix_schema():
    print("--- FIXING DATABASE SCHEMA ---")
    
    # We need to use "isolation_level='AUTOCOMMIT'" for ALTER TYPE in some drivers, 
    # but create_async_engine handles it if we use .execution_options
    
    # Or simply:
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            print("Adding 'QUEUED' to orderstatusenum...")
            await conn.execute(text("ALTER TYPE orderstatusenum ADD VALUE 'QUEUED'"))
            print("SUCCESS: Added QUEUED")
        except Exception as e:
            msg = str(e)
            if "DuplicateObjectError" in msg or "already exists" in msg:
                print("SKIPPED: QUEUED already exists.")
            else:
                print(f"ERROR Adding QUEUED: {e}")
                
        try:
            print("Adding 'PRINTING' to orderstatusenum...")
            await conn.execute(text("ALTER TYPE orderstatusenum ADD VALUE 'PRINTING'"))
            print("SUCCESS: Added PRINTING")
        except Exception as e:
            msg = str(e)
            if "DuplicateObjectError" in msg or "already exists" in msg:
                 print("SKIPPED: PRINTING already exists.")
            else:
                 print(f"ERROR Adding PRINTING: {e}")

    print("--- SCHEMA FIX COMPLETE ---")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_schema())
