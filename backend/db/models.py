from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.database import Base

class Gender(Base):
    __tablename__ = "genders"
    
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50), unique=True, nullable=False)
    
    # Relationships
    products = relationship("Product", back_populates="gender")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Self-referencing relationship
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    
    # Products relationship
    products = relationship("Product", back_populates="category")

class Color(Base):
    __tablename__ = "colors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    
    # Relationships
    variants = relationship("ProductVariant", back_populates="color")

class Size(Base):
    __tablename__ = "sizes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer)
    
    # Relationships
    variants = relationship("ProductVariant", back_populates="size")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    gender_id = Column(Integer, ForeignKey("genders.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    category = relationship("Category", back_populates="products")
    gender = relationship("Gender", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    sku = Column(String(100), unique=True, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=True)
    color_id = Column(Integer, ForeignKey("colors.id"))
    size_id = Column(Integer, ForeignKey("sizes.id"))
    in_stock = Column(Integer, nullable=False)
    dimensions = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="variants")
    color = relationship("Color", back_populates="variants")
    size = relationship("Size", back_populates="variants")
    images = relationship("ProductImage", back_populates="variant", cascade="all, delete-orphan")

class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    url = Column(Text, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="images")
    variant = relationship("ProductVariant", back_populates="images")