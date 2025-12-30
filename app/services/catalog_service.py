import os
import re
from typing import List, Set
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product_sku import ProductSKU

class ProductDisplayDTO(BaseModel):
    """
    Data Transfer Object for displaying products in the frontend catalog.
    Contains the master SKU info, aggregated colors, and material tags.
    """
    id: int
    sku: str
    name: str
    printfile_display_name: str
    variant_colors: List[str]
    material_tags: List[str]

def _strip_uuid_prefix(path: str) -> str:
    """
    Utility to strip UUID prefixes from filenames.
    Assumes format: storage/3mf/UUID-filename.3mf or similar.
    """
    basename = os.path.basename(path)
    # Pattern for UUID (8-4-4-4-12 hex chars) followed by a dash
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-?"
    return re.sub(uuid_pattern, "", basename)

async def get_public_catalog(session: AsyncSession) -> List[ProductDisplayDTO]:
    """
    Fetches all public-facing products (Master SKUs) and aggregates 
    metadata from their variants.
    """
    # 1. Fetch parent SKUs that are visible in the catalog
    # We load 'product' (master data) and 'children' (variants) eagerly.
    # We also load 'children.product' to access material requirements.
    statement = (
        select(ProductSKU)
        .where(ProductSKU.is_catalog_visible == True)
        .where(ProductSKU.parent_id == None)
        .options(
            selectinload(ProductSKU.product),
            selectinload(ProductSKU.print_file),
            selectinload(ProductSKU.children).selectinload(ProductSKU.product)
        )
    )
    
    result = await session.execute(statement)
    parent_skus = result.scalars().all()
    
    catalog: List[ProductDisplayDTO] = []
    
    for parent in parent_skus:
        unique_colors: Set[str] = set()
        material_tags: Set[str] = set()
        
        # Determine Print File Display Name
        display_name = "No File"
        if parent.print_file:
            display_name = parent.print_file.display_name
        elif parent.product and parent.product.file_path_3mf:
            # Fallback for legacy data
            display_name = _strip_uuid_prefix(parent.product.file_path_3mf)
            
        if parent.product and parent.product.required_filament_type:
            material_tags.add(parent.product.required_filament_type)
        
        # 2. Extract unique hex colors and materials from children variants
        for child in parent.children:
            # Color Aggregation
            if child.hex_color:
                unique_colors.add(child.hex_color)
            
            # Material Aggregation
            if child.product and child.product.required_filament_type:
                material_tags.add(child.product.required_filament_type)
            
            # If child has its own file path (rare for variants but possible)
            if child.product and display_name == "No File":
                display_name = _strip_uuid_prefix(child.product.file_path_3mf)

        # Final DTO
        dto = ProductDisplayDTO(
            id=parent.id,
            sku=parent.sku,
            name=parent.name,
            printfile_display_name=display_name,
            variant_colors=sorted(list(unique_colors)),
            material_tags=sorted(list(material_tags))
        )
        catalog.append(dto)
        
    return catalog
