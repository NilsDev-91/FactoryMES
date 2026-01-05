from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import text, select
import logging
import asyncio
import os
import sys

# Windows fixes for MQTT/aiomqtt - Must be set BEFORE any async code runs
# Python 3.8+ on Windows uses ProactorEventLoop by default, which is incompatible with aiomqtt
# This must happen at module load time, before FastAPI creates its event loop
if sys.platform.startswith("win"):
    if sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Also explicitly set a new event loop to ensure the policy takes effect
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.models import * # Load all models for metadata discovery
from app.models.core import SQLModel, Printer
from app.routers import system, printers, products, orders, ebay, auth, printer_control, fms
from app.services.printer.mqtt_worker import PrinterMqttWorker
from app.core.redis import close_redis_connection
# NEU: Importiere die Dispatcher Klasse
from app.services.production.dispatcher import ProductionDispatcher 
from app.services.production.order_processor import order_processor 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("🚀 FactoryOS Starting up...")
    
    # 1. Database Check
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("✅ Database connected.")
    except Exception as e:
        logger.error(f"❌ DB Connection Failed: {e}")
        raise RuntimeError("Database unreachable") from e
    
    # 2. Start MQTT Workers
    app.state.mqtt_tasks = {}
    try:
        mqtt_worker = PrinterMqttWorker()
        async with async_session_maker() as session:
            result = await session.execute(select(Printer))
            printers_list = result.scalars().all()
            
            for printer in printers_list:
                if printer.ip_address and printer.access_code:
                    task = asyncio.create_task(
                        mqtt_worker.start_listening(printer.ip_address, printer.access_code, printer.serial)
                    )
                    app.state.mqtt_tasks[printer.serial] = task
                    logger.info(f"👂 MQTT Listener started for {printer.serial}")

    except Exception as e:
        logger.error(f"Lifespan ERROR: Failed to initialize MQTT workers: {e}", exc_info=True)

    # 3. Start Production Dispatcher
    try:
        logger.info("🧠 Launching Production Dispatcher...")
        dispatcher = ProductionDispatcher()
        app.state.dispatcher = dispatcher
        app.state.dispatcher_task = asyncio.create_task(dispatcher.start())
    except Exception as e:
        logger.error(f"Lifespan ERROR: Failed to initialize Production Dispatcher: {e}", exc_info=True)

    # 4. Start eBay Order Processor
    try:
        app.state.order_processor = order_processor
        app.state.order_processor_task = asyncio.create_task(order_processor.start_loop())
        logger.info("📦 eBay Order Processor Loop started.")
    except Exception as e:
        logger.error(f"Lifespan ERROR: Failed to initialize eBay Order Processor: {e}", exc_info=True)

    yield
    
    # --- SHUTDOWN ---
    logger.info("🛑 Shutting down FactoryOS...")
    
    # Stop Dispatcher
    if hasattr(app.state, "dispatcher"):
        await app.state.dispatcher.stop()
    if hasattr(app.state, "dispatcher_task"):
        app.state.dispatcher_task.cancel()
    
    # Stop Order Processor
    if hasattr(app.state, "order_processor"):
        app.state.order_processor.running = False
    if hasattr(app.state, "order_processor_task"):
        app.state.order_processor_task.cancel()
        
    # Stop MQTT
    if hasattr(app.state, "mqtt_tasks"):
        for task in app.state.mqtt_tasks.values():
            task.cancel()
        await asyncio.gather(*app.state.mqtt_tasks.values(), return_exceptions=True)
    
    # Close Redis Connection
    await close_redis_connection()
    logger.info("✅ Redis connection closed.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    # Explicitly allow frontend origin to support allow_credentials=True
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:5173", # Vite Default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000", # Self-reference
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(ebay.router, prefix="/api")
app.include_router(printers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(printer_control.router, prefix="/api")
app.include_router(fms.router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "online", "system": "FactoryOS v2.0"}