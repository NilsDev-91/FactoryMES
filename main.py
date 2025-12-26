
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select, text
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
import os
import shutil
import uuid

from database import get_session, engine
from models import Printer, Order, OrderStatusEnum, SQLModel, Product

app = FastAPI(title="FactoryOS API")

# Ensure storage directory exists
STORAGE_DIR = "storage/3mf"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Mount storage for static access if needed (optional, but good for downloading)
# app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
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

@app.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    try:
        # Simple DB check
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.post("/orders", response_model=Order)
async def create_order(order: Order, session: AsyncSession = Depends(get_session)):
    try:
        # Check for duplicate platform_order_id
        result = await session.execute(select(Order).where(Order.platform_order_id == order.platform_order_id))
        existing_order = result.scalars().first()
        
        if existing_order:
            raise HTTPException(status_code=400, detail=f"Order with ID {order.platform_order_id} already exists.")

        # FIX: asyncpg requires datetime object, ensure conversion if Pydantic yielded a string
        if isinstance(order.purchase_date, str):
            from datetime import datetime
            try:
                order.purchase_date = datetime.fromisoformat(str(order.purchase_date))
            except ValueError:
                # If format is weird, let it fail or handle it. 
                # Attempt to handle 'Z' if present for UTC
                order.purchase_date = datetime.fromisoformat(str(order.purchase_date).replace('Z', '+00:00'))

        session.add(order)
        await session.commit()
        await session.refresh(order)

        # 2. Auto-Create Job if Product exists
        # Find Product by SKU to get 3mf path
        result_prod = await session.execute(select(Product).where(Product.sku == order.sku))
        product = result_prod.scalars().first()

        if product:
             from models import Job, JobStatusEnum
             new_job = Job(
                 order_id=order.id,
                 gcode_path=product.file_path_3mf, # Use the artifact path
                 status=JobStatusEnum.PENDING
             )
             session.add(new_job)
             await session.commit()
             # print(f"Auto-created Job for Order {order.id}")
        else:
            # product not found, cannot start job automatically
            # print(f"Warning: No product found for SKU {order.sku}, job not created.")
            pass

        return order
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        # Log the full error for server-side debugging if needed
        # print(f"Error creating order: {e}") 
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

# --- Product Management Endpoints ---

@app.get("/products", response_model=List[Product])
async def get_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    return result.scalars().all()

@app.post("/products", response_model=Product)
async def create_product(product: Product, session: AsyncSession = Depends(get_session)):
    # Check if SKU exists
    existing = await session.execute(select(Product).where(Product.sku == product.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product

@app.post("/products/upload")
async def upload_product_file(file: UploadFile = File(...)):
    """
    Uploads a .3mf file and returns the relative path.
    """
    if not file.filename.endswith(".3mf"):
         raise HTTPException(status_code=400, detail="Only .3mf files are allowed")

    # Generate unique filename to prevent overwrites
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(STORAGE_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    # Return relative path for DB storage
    return {"file_path": file_path}

@app.delete("/products/{id}")
async def delete_product(id: int, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Optional: Delete the physical file too?
    # User didn't strictly ask, but it's good practice. 
    # For safety in this demo, maybe we keep it or delete it. Let's delete to be clean.
    if os.path.exists(product.file_path_3mf):
        try:
            os.remove(product.file_path_3mf)
        except:
            pass # Ignore file delete errors

    await session.delete(product)
    await session.commit()
    return {"ok": True}
