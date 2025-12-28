from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import os
import shutil
import uuid

from app.core.database import get_session
from app.models.core import Product

router = APIRouter(prefix="/products", tags=["Products"])

STORAGE_DIR = "storage/3mf"

@router.get("", response_model=List[Product])
async def get_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    return result.scalars().all()

@router.post("", response_model=Product)
async def create_product(product: Product, session: AsyncSession = Depends(get_session)):
    # 1. Validate File Path exists
    if not os.path.exists(product.file_path_3mf):
        raise HTTPException(status_code=400, detail=f"3MF File not found at path: {product.file_path_3mf}. Please upload it first.")

    # 2. Check if SKU exists
    existing = await session.execute(select(Product).where(Product.sku == product.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product

@router.post("/upload")
async def upload_product_file(file: UploadFile = File(...)):
    """
    Step 1 of Product Creation: Upload the 3MF file.
    Returns: {"file_path": "storage/3mf/uuid_filename.3mf"}
    """
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    if not file.filename.endswith(".3mf"):
         raise HTTPException(status_code=400, detail="Only .3mf files are allowed")

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(STORAGE_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    return {"file_path": file_path}

@router.delete("/{id}")
async def delete_product(id: int, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if os.path.exists(product.file_path_3mf):
        try:
            os.remove(product.file_path_3mf)
        except:
            pass 

    await session.delete(product)
    await session.commit()
    return {"ok": True}

@router.patch("/{id}", response_model=Product)
async def update_product(id: int, product_update: dict, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product_update.items():
        if hasattr(product, key):
            setattr(product, key, value)
    
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product
