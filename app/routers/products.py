from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.concurrency import run_in_threadpool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
import os
import shutil
import uuid
import zipfile
import io

from app.core.database import get_session
from app.models.core import Product
from app.models.product_sku import ProductSKU
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])

STORAGE_DIR = "storage/3mf"

from app.services.catalog_service import get_public_catalog, ProductDisplayDTO
from app.services.product_service import ProductService, ProductCreateDTO, ProductUpdateDTO, ProductReadDTO

@router.get("", response_model=List[ProductDisplayDTO])
async def get_products(session: AsyncSession = Depends(get_session)):
    """
    Returns the public catalog using the refined Master-Variant DTO.
    """
    return await get_public_catalog(session)

@router.get("/{id}", response_model=ProductReadDTO)
async def get_product(id: int, session: AsyncSession = Depends(get_session)):
    product = await ProductService.get_product(id, session)
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
    Handles ProductSKU IDs.
    """
    # 1. Fetch as ProductSKU with eager loading
    statement = (
        select(ProductSKU)
        .where(ProductSKU.id == id)
        .options(
            selectinload(ProductSKU.print_file),
            selectinload(ProductSKU.product).selectinload(Product.print_file)
        )
    )
    result = await session.execute(statement)
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(status_code=404, detail="Product SKU not found")
    
    # 2. Resolve file path logic
    file_path = None
    
    # Priority 1: SKU-specific print file
    if sku.print_file:
        file_path = sku.print_file.file_path
    
    # Priority 2: Parent Product print file
    elif sku.product and sku.product.print_file:
        file_path = sku.product.print_file.file_path
        
    # Priority 3: Legacy Parent Product file path
    elif sku.product and sku.product.file_path_3mf:
        file_path = sku.product.file_path_3mf
         
    if not file_path or not os.path.exists(file_path):
        # Return 404 instead of 500 to prevent crashing
        raise HTTPException(status_code=404, detail="Print file not found")

    # 3. Generate thumbnail safely
    try:
        # Run blocking zip extraction in threadpool
        thumbnail_data = await run_in_threadpool(extract_thumbnail_sync, file_path)
    except Exception as e:
        print(f"Thumbnail generation exception: {e}")
        # Don't crash
        raise HTTPException(status_code=404, detail="Failed to generate thumbnail")

    if not thumbnail_data:
        raise HTTPException(status_code=404, detail="Thumbnail not found in 3MF archive")

    return Response(content=thumbnail_data, media_type="image/png")

@router.post("", response_model=ProductReadDTO)
async def create_product(product_dto: ProductCreateDTO, session: AsyncSession = Depends(get_session)):
    """
    Standard Product Creation (Master).
    Supported optional procedural generation.
    """
    return await ProductService.create_product(product_dto, session)

from datetime import datetime
from app.models.print_file import PrintFile

@router.post("/upload")
async def upload_product_file(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    """
    Step 1 of Product Creation: Upload the 3MF file.
    Creates a PrintFile entity.
    Returns: {"id": 123, "file_path": "storage/3mf/uuid_filename.3mf"}
    """
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    if not file.filename.endswith(".3mf") and not file.filename.endswith(".gcode"):
         raise HTTPException(status_code=400, detail="Only .3mf or .gcode files are allowed")

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(STORAGE_DIR, unique_filename)
    
    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    # Create PrintFile Entity
    print_file = PrintFile(
        file_path=file_path,
        file_size_bytes=file_size,
        uploaded_at=datetime.utcnow(),
        original_filename=file.filename
    )
    session.add(print_file)
    await session.commit()
    await session.refresh(print_file)

    return {"id": print_file.id, "file_path": file_path}

@router.delete("/{id}")
async def delete_product(id: int, session: AsyncSession = Depends(get_session)):
    # 1. Try to fetch as ProductSKU (Frontend Catalog Logic)
    sku = await session.get(ProductSKU, id)
    if sku:
        # It's a SKU (Catalog Item)
        # Optional: Cascade delete to Parent Product if this is the Master/Only SKU?
        # For now, safe delete of the SKU entry.
        await session.delete(sku)
        await session.commit()
        return {"ok": True}

    # 2. Fallback: Try to fetch as Product (Legacy/Raw Access)
    product = await session.get(Product, id)
    if product:
        if os.path.exists(product.file_path_3mf):
            try:
                os.remove(product.file_path_3mf)
            except:
                pass 
        await session.delete(product)
        await session.commit()
        return {"ok": True}

    raise HTTPException(status_code=404, detail="Product or SKU not found")

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
        
        variant = ProductSKU(
            sku=sku,
            name=f"{request.name} ({var.color_name or 'Default'})",
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
