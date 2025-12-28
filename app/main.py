from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import text
import logging

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.models.core import SQLModel, Printer
from app.models.order import Order, OrderItem
from app.routers import system, printers, products, orders, ebay, auth
from app.services.printer.mqtt_worker import PrinterMqttWorker
import asyncio
from sqlmodel import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check DB connectivity
    logger.info("Checking database connectivity...")
    try:
        async with engine.begin() as conn:
            # Verify we can ping the DB
            await conn.execute(text("SELECT 1"))
            # Auto-create tables (Safe for dev, in prod use migrations)
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database connectivity verified.")
    except Exception as e:
        logger.error(f"DATABASE CONNECTION REFUSED: {str(e)}")
        # We want the app to fail if the DB is unreachable
        raise RuntimeError("Could not connect to database on startup.") from e
    
    # Startup: Start MQTT Workers
    mqtt_worker = PrinterMqttWorker(settings)
    app.state.mqtt_tasks = {}
    
    async with async_session_maker() as session:
        statement = select(Printer)
        result = await session.execute(statement)
        printers_list = result.scalars().all()
        
        for printer in printers_list:
            if printer.ip_address and printer.access_code:
                task = asyncio.create_task(
                    mqtt_worker.start_listening(
                        printer.ip_address, 
                        printer.access_code, 
                        printer.serial
                    )
                )
                app.state.mqtt_tasks[printer.serial] = task
                logger.info(f"Scheduled MQTT worker for printer {printer.serial}")

    yield
    
    # Shutdown: Cancel all MQTT tasks
    logger.info("Shutting down application...")
    if hasattr(app.state, "mqtt_tasks"):
        for serial, task in app.state.mqtt_tasks.items():
            logger.info(f"Cancelling MQTT worker for printer {serial}")
            task.cancel()
        
        # Wait for all tasks to be cancelled
        await asyncio.gather(*app.state.mqtt_tasks.values(), return_exceptions=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unified API Prefix: /api
app.include_router(auth.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(ebay.router, prefix="/api")
app.include_router(printers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(orders.router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

@app.get("/")
async def root():
    return {"message": "FactoryOS API is running", "docs": "/docs"}
