from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class GenderBase(BaseModel):
    label: str

class GenderCreate(GenderBase):
    pass

class Gender(GenderBase):
    id: int
    
    class Config:
        from_attributes = True

class ColorBase(BaseModel):
    name: str
    slug: str

class ColorCreate(ColorBase):
    pass

class Color(ColorBase):
    id: int
    
    class Config:
        from_attributes = True

class SizeBase(BaseModel):
    name: str
    slug: str
    sort_order: Optional[int] = None

class SizeCreate(SizeBase):
    pass

class Size(SizeBase):
    id: int
    
    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    slug: str
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    children: List['Category'] = []
    
    class Config:
        from_attributes = True

# Product schemas
class ProductImageBase(BaseModel):
    url: str
    variant_id: Optional[int] = None

class ProductImageCreate(ProductImageBase):
    product_id: int

class ProductImage(ProductImageBase):
    id: int
    product_id: int
    
    class Config:
        from_attributes = True

class ProductVariantBase(BaseModel):
    sku: str
    price: Decimal
    sale_price: Optional[Decimal] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    in_stock: int
    dimensions: Optional[str] = None

class ProductVariantCreate(ProductVariantBase):
    product_id: int

class ProductVariant(ProductVariantBase):
    id: int
    product_id: int
    created_at: datetime
    color: Optional[Color] = None
    size: Optional[Size] = None
    images: List[ProductImage] = []
    
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    gender_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[Category] = None
    gender: Optional[Gender] = None
    variants: List[ProductVariant] = []
    images: List[ProductImage] = []
    
    class Config:
        from_attributes = True

# Stock check request (updated for new schema)
class StockRequest(BaseModel):
    productName: str
    quantity: int
    color: Optional[str] = None
    size: Optional[str] = None

class ProductResponse(StockRequest):
    pass

# Invoice and order schemas (updated)
class InvoiceRequest(BaseModel):
    customer_name: str
    customer_contact: str
    customer_address: str
    sku: str
    product_name: str
    quantity_needed: int
    total_price: float

class InvoiceToolRequest(BaseModel):
    customer_name: str
    customer_contact: str
    customer_address: str
    product_name: str
    quantity_needed: int
    total_price: float
    color: Optional[str]
    size: Optional[str]

class StockUpdate(BaseModel):
    sku: str
    quantity_needed: int

class ChatRequest(BaseModel):
    sessionId: str
    message: str

class SessionStatus(str, Enum):
    AGENT_CONTROL = "under-agent-control"
    HUMAN_CONTROL = "under-human-control"
    NEED_HUMAN_SUPPORT = "need-human-support"

class HITLSession(BaseModel):
    session_id: str
    customer_number: str
    status: SessionStatus
    last_message: Optional[str] = None
    updated_at: datetime

class HITLMessage(BaseModel):
    sender: str  # "agent" | "human" | "customer"
    text: str
    timestamp: datetime

class HumanReplyRequest(BaseModel):
    text: str

# CSV Import schema
class ProductCSVRow(BaseModel):
    product_name: str
    description: Optional[str] = None
    category_name: str
    category_slug: str
    parent_category: Optional[str] = None
    gender_label: str
    variant_sku: str
    price: Decimal
    sale_price: Optional[Decimal] = None
    color_name: str
    color_slug: str
    size_name: str
    size_slug: str
    size_order: Optional[int] = None
    stock_quantity: int
    dimensions: Optional[str] = None
    image_urls: str  