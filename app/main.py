from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import text, select
import logging
import asyncio

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.models.core import SQLModel, Printer
from app.routers import system, printers, products, orders, ebay, auth
from app.services.printer.mqtt_worker import PrinterMqttWorker
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
    
    # 2. Start MQTT Workers (The Ears)
    mqtt_worker = PrinterMqttWorker()
    app.state.mqtt_tasks = {}
    
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

    # 3. Start Production Dispatcher (The Brain & Hands)
    dispatcher = ProductionDispatcher()
    # Wir speichern die Instanz in app.state, um sie beim Shutdown zu stoppen
    app.state.dispatcher = dispatcher
    # Startet die Endlosschleife im Hintergrund
    app.state.dispatcher_task = asyncio.create_task(dispatcher.start())
    app.state.dispatcher_task = asyncio.create_task(dispatcher.start())
    logger.info("🧠 Production Dispatcher Loop started.")

    # 4. Start eBay Order Processor
    app.state.order_processor = order_processor
    app.state.order_processor_task = asyncio.create_task(order_processor.start_loop())
    logger.info("📦 eBay Order Processor Loop started.")

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

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Für Dev offen lassen
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

@app.get("/")
async def root():
    return {"status": "online", "system": "FactoryOS v2.0"}