
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from database import get_session, engine
from models import Printer, Order, OrderStatusEnum, SQLModel

app = FastAPI(title="FactoryOS API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Create Tables (Simple migration strategy)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Endpoints

@app.get("/printers", response_model=List[Printer])
async def get_printers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Printer))
    return result.scalars().all()

@app.get("/orders", response_model=List[Order])
async def get_orders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Order))
    return result.scalars().all()

@app.post("/orders", response_model=Order)
async def create_order(order: Order, session: AsyncSession = Depends(get_session)):
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order
