import sys
import asyncio
import uvicorn
import os

if __name__ == "__main__":
    # CRITICAL FIX: Force SelectorEventLoop on Windows for MQTT compatibility
    # This must run BEFORE uvicorn starts the event loop.
    if sys.platform.startswith("win"):
        try:
            # Check for Python 3.8+ Windows policy
            policy = asyncio.WindowsSelectorEventLoopPolicy()
            asyncio.set_event_loop_policy(policy)
            print("🔧 Windows SelectorEventLoopPolicy enforce: SUCCESS")
        except AttributeError:
            pass # Not on Windows or policy not available

    # Start Uvicorn programmatically
    print("🚀 Starting FactoryOS via Custom Launcher...")
    # Reload is enabled for dev experience
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
