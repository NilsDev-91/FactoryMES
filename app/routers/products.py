from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.concurrency import run_in_threadpool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import os
import shutil
import uuid
import zipfile
import io

from app.core.database import get_session
from app.models.core import Product, ProductVariant
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])

STORAGE_DIR = "storage/3mf"

@router.get("", response_model=List[Product])
async def get_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    return result.scalars().all()

@router.get("/{id}", response_model=Product)
async def get_product(id: int, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

def extract_thumbnail_sync(file_path: str) -> Optional[bytes]:
    try:
        if not os.path.exists(file_path):
            return None
        
        with zipfile.ZipFile(file_path, 'r') as z:
            # Common locations for 3MF thumbnails (Bambu/Prusa)
            targets = ["Metadata/thumbnail.png", "thumbnail.png", "Metadata/plate_1.png"]
            
            for target in targets:
                if target in z.namelist():
                    return z.read(target)
            
            # Fallback: check any .png in Metadata
            for name in z.namelist():
                if name.startswith("Metadata/") and name.endswith(".png"):
                    return z.read(name)
                    
    except Exception as e:
        print(f"Thumbnail extraction failed: {e}")
        return None
    return None

@router.get("/{id}/thumbnail")
async def get_product_thumbnail(id: int, session: AsyncSession = Depends(get_session)):
    """
    Extracts the embedded thumbnail from the .3mf file.
    Returns the image bytes directly.
    """
    product = await session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.file_path_3mf:
        raise HTTPException(status_code=404, detail="No 3MF file associated with this product")

    # Run blocking zip extraction in threadpool
    thumbnail_data = await run_in_threadpool(extract_thumbnail_sync, product.file_path_3mf)

    if not thumbnail_data:
        # Return a simple 1x1 transparent pixel or 404? 
        # 404 allows frontend to show a fallback icon easily.
        raise HTTPException(status_code=404, detail="Thumbnail not found in 3MF archive")

    return Response(content=thumbnail_data, media_type="image/png")

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

class VariantDefinition(BaseModel):
    hex_code: str
    color_name: Optional[str] = "Unknown"

class ProductDefinitionRequest(BaseModel):
    name: str
    filename_3mf: str
    allowed_variants: List[VariantDefinition]

@router.post("/create-with-variants", response_model=Product)
async def create_product_with_variants(
    request: ProductDefinitionRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Creates a Parent Product and generates SKUs for each variant.
    Atomic Transaction.
    """
    # 1. Validate File
    # Ensure filename provided exists in STORAGE_DIR
    full_path = os.path.join(STORAGE_DIR, request.filename_3mf)
    if not os.path.exists(full_path):
        # Fallback: check if path is absolute or relative to root
        if not os.path.exists(request.filename_3mf):
             raise HTTPException(status_code=400, detail=f"3MF File not found: {request.filename_3mf}")
        full_path = request.filename_3mf

    # 3. Create Parent Product
    # Since SKU is NOT NULL in DB, we generate a placeholder for the parent
    parent_sku = f"PARENT_{uuid.uuid4()}"
    
    new_product = Product(
        name=request.name,
        file_path_3mf=full_path,
        sku=parent_sku, 
        required_filament_type="PLA", 
    )
    session.add(new_product)
    
    variants_list = []
    
    for var in request.allowed_variants:
        sanitized_prod = request.name.upper().replace(" ", "_")
        sanitized_color = var.color_name.upper().replace(" ", "_")
        
        if sanitized_color == "UNKNOWN":
             sku = f"{sanitized_prod}_{var.hex_code.upper()[-6:]}" # Use last 6 chars of hex to handle potential alpha channel
        else:
             sku = f"{sanitized_prod}_{sanitized_color}"
        
        variant = ProductVariant(
            sku=sku,
            hex_color=var.hex_code,
            color_name=var.color_name or "Unknown",
            product=new_product 
        )
        variants_list.append(variant)
    
    session.add_all(variants_list) 
    
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create product: {str(e)}")
        
    await session.refresh(new_product, ["variants"])
    return new_product
