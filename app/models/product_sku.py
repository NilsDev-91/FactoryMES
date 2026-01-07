from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .core import Product, ProductRequirement
    from .print_file import PrintFile

class ProductSKU(SQLModel, table=True):
    """
    ProductSKU represents a specific version of a product, using a hierarchical 
    'Master-Variant' architecture.
    
    The parent_id is used for grouping variants (e.g., specific colors) under 
    a main product master SKU.
    
    is_catalog_visible allows hiding specific technical or internal SKUs 
    from being listed in the main user-facing catalog.

    Deleting a Parent SKU automatically removes all Child Variants.
    """
    __tablename__ = "product_skus"

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name: str
    is_catalog_visible: bool = Field(default=True)
    
    # Hierarchy
    parent_id: Optional[int] = Field(default=None, foreign_key="product_skus.id")
    
    # Original fields from ProductVariant (integrated)
    product_id: Optional[int] = Field(default=None, foreign_key="products.id")
    hex_color: Optional[str] = None
    color_name: Optional[str] = None
    
    # New: Single Source of Truth for assets
    print_file_id: Optional[int] = Field(default=None, foreign_key="print_files.id")
    
    # Relationships
    product: Optional["Product"] = Relationship(back_populates="variants")
    print_file: Optional["PrintFile"] = Relationship()
    
    # Self-referential hierarchy
    # We use 'remote_side' on the parent relationship for the adjacency list.
    parent: Optional["ProductSKU"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "ProductSKU.id"
        }
    )
    children: List["ProductSKU"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan"
        }
    )
    # requirements: List["ProductRequirement"] = Relationship(
    #     back_populates="product_sku",
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    # )
