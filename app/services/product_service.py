import uuid
from typing import List, Optional, Set
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from fastapi import HTTPException

from app.models.core import Product, ProductRequirement
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile
from app.models.filament import FilamentProfile

# --- DTOs ---

class PrintFileSummaryDTO(BaseModel):
    id: int
    original_filename: str
    file_path: str

class ProductRequirementSummaryDTO(BaseModel):
    filament_profile_id: uuid.UUID
    material: str
    color_hex: str
    brand: str

class ProductSKUReadDTO(BaseModel):
    id: int
    sku: str
    name: str
    hex_color: Optional[str] = None
    color_name: Optional[str] = None
    is_catalog_visible: bool
    print_file: Optional[PrintFileSummaryDTO] = None
    requirements: List[ProductRequirementSummaryDTO] = []

class ProductReadDTO(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    is_catalog_visible: bool
    print_file_id: Optional[int] = None
    print_file: Optional[PrintFileSummaryDTO] = None
    variants: List[ProductSKUReadDTO] = []
    created_at: datetime

class VariantDefinitionDTO(BaseModel):
    hex_code: str
    color_name: str

class ProductCreateDTO(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    print_file_id: Optional[int] = None
    generate_variants_for_profile_ids: Optional[List[uuid.UUID]] = None

class ProductUpdateDTO(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    print_file_id: Optional[int] = None
    is_catalog_visible: Optional[bool] = None

# --- Service Implementation ---

class ProductService:
    @staticmethod
    async def create_product(dto: ProductCreateDTO, session: AsyncSession) -> Product:
        # 1. Validation
        if dto.print_file_id:
            print_file = await session.get(PrintFile, dto.print_file_id)
            if not print_file:
                raise HTTPException(status_code=404, detail="PrintFile not found")

        # Check for Master SKU collision (Product Table)
        existing_product = await session.execute(select(Product).where(Product.sku == dto.sku))
        if existing_product.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"SKU '{dto.sku}' already exists in Products.")

        # Check for Master SKU collision (ProductSKU Table)
        existing_sku = await session.execute(select(ProductSKU).where(ProductSKU.sku == dto.sku))
        if existing_sku.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"SKU '{dto.sku}' already exists in Variants.")

        # 2. Create Master Product
        # We generate a unique master SKU if not provided, though the DTO requires it
        master_product = Product(
            name=dto.name,
            sku=dto.sku,
            description=dto.description,
            print_file_id=dto.print_file_id,
            is_catalog_visible=True
        )
        session.add(master_product)
        await session.flush() # Flush to get master_product.id

        # 3. Create Master SKU (Adjacency List Root)
        master_sku = ProductSKU(
            sku=dto.sku,
            name=dto.name,
            is_catalog_visible=True,
            product_id=master_product.id,
            print_file_id=dto.print_file_id
        )
        session.add(master_sku)
        await session.flush()

        # 4. Procedural Variant Generation
        if dto.generate_variants_for_profile_ids:
            for profile_id in dto.generate_variants_for_profile_ids:
                profile = await session.get(FilamentProfile, profile_id)
                if not profile:
                    continue # Or raise error? Let's skip invalid profiles for now.

                # Sanitize components for SKU
                safe_name = dto.name.replace(" ", "_").upper()
                safe_mat = profile.material.replace(" ", "_").upper()
                safe_color = profile.color_hex.replace("#", "").upper()
                
                variant_sku_str = f"{dto.sku}-{safe_mat}-{safe_color}"
                
                # Check for SKU collisions
                existing = await session.execute(select(ProductSKU).where(ProductSKU.sku == variant_sku_str))
                if existing.scalar_one_or_none():
                    continue

                # Create Child SKU
                child_sku = ProductSKU(
                    sku=variant_sku_str,
                    name=f"{dto.name} - {profile.material} ({profile.color_hex})",
                    is_catalog_visible=False,
                    parent_id=master_sku.id,
                    product_id=master_product.id,
                    print_file_id=dto.print_file_id, # Inherit file from master
                    hex_color=profile.color_hex
                )
                session.add(child_sku)
                await session.flush()

                # Create Requirement
                req = ProductRequirement(
                    product_sku_id=child_sku.id,
                    filament_profile_id=profile.id
                )
                session.add(req)

        master_id = master_product.id
        await session.commit()
        
        # 5. Full Reload to prevent MissingGreenlet/ResponseValidation errors
        # We must load all relation dependencies that the response model expects
        statement = (
            select(Product)
            .where(Product.id == master_id)
            .options(
                selectinload(Product.print_file),
                selectinload(Product.variants).selectinload(ProductSKU.print_file),
                selectinload(Product.variants).selectinload(ProductSKU.requirements).selectinload(ProductRequirement.filament_profile)
            )
        )
        result = await session.execute(statement)
        return result.scalar_one()

    @staticmethod
    async def get_product(product_id: int, session: AsyncSession) -> Optional[Product]:
        # 1. Try Direct Lookup
        statement = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.print_file),
                selectinload(Product.variants).selectinload(ProductSKU.print_file),
                selectinload(Product.variants).selectinload(ProductSKU.requirements).selectinload(ProductRequirement.filament_profile)
            )
        )
        result = await session.execute(statement)
        product = result.scalar_one_or_none()

        if product:
            return product

        # 2. Fallback: Lookup via ProductSKU ID (ID resolution for catalog)
        sku = await session.get(ProductSKU, product_id)
        if sku and sku.product_id:
            return await ProductService.get_product(sku.product_id, session)

        return None

    @staticmethod
    async def list_products(session: AsyncSession) -> List[Product]:
        statement = (
            select(Product)
            .options(
                selectinload(Product.print_file),
                selectinload(Product.variants).selectinload(ProductSKU.print_file)
            )
        )
        result = await session.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def update_product(product_id: int, dto: ProductUpdateDTO, session: AsyncSession) -> Optional[Product]:
        product = await ProductService.get_product(product_id, session)
        if not product:
            return None

        # Update Parent Product
        if dto.name is not None:
            product.name = dto.name
        if dto.sku is not None:
            # Check for collision if changing SKU
            if dto.sku != product.sku:
                 existing = await session.execute(select(Product).where(Product.sku == dto.sku))
                 if existing.scalar_one_or_none():
                      raise HTTPException(status_code=409, detail=f"SKU '{dto.sku}' already exists.")
            product.sku = dto.sku
        if dto.description is not None:
            product.description = dto.description
        if dto.print_file_id is not None:
            product.print_file_id = dto.print_file_id
        if dto.is_catalog_visible is not None:
            product.is_catalog_visible = dto.is_catalog_visible

        # Sync to Master SKU (the one directly owned by this product, no parent)
        # This keeps the catalog view in sync with the master product data
        for variant in product.variants:
            if variant.parent_id is None: # This is the master
                if dto.name is not None:
                    variant.name = dto.name
                if dto.sku is not None:
                    variant.sku = dto.sku
                if dto.print_file_id is not None:
                    variant.print_file_id = dto.print_file_id

        actual_id = product.id
        session.add(product)
        await session.commit()
        return await ProductService.get_product(actual_id, session)
