from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from backend.db.models import Product, ProductVariant, Color, Size
from backend.db.schema import StockRequest  

def _decimal_to_float(d: Optional[Decimal]) -> Optional[float]:
    if d is None:
        return None
    return float(d)

def get_product_stock_status(data: StockRequest, db: Session) -> Dict[str, Any]:
    """
    Option 3 flow:
    1) Try SKU first.
    2) If product name only: 
        - return available colors & sizes if color/size not provided.
        - check stock for exact variant if color & size provided.
    3) Aggregate fallback if no variant matches.
    """
    name_or_sku = data.productName.strip()

    # 1) Try exact SKU match first
    variant = db.query(ProductVariant).filter(ProductVariant.sku == name_or_sku).first()
    if variant:
        return {
            "type": "variant",
            "sku": variant.sku,
            "product_id": variant.product_id,
            "product_name": variant.product.name if variant.product else None,
            "available_qty": variant.in_stock,
            "price": _decimal_to_float(variant.price),
            "sale_price": _decimal_to_float(variant.sale_price),
            "in_stock": variant.in_stock >= data.quantity
        }

    # 2) Find product by name
    product = db.query(Product).filter(Product.name.ilike(f"%{name_or_sku}%")).first()
    if not product:
        return {"error": "Product not found"}

    # 2a) If color/size not provided, return available options
    if not getattr(data, "color", None) and not getattr(data, "size", None):
        variants = product.variants
        available_colors = list({v.color.name for v in variants if v.color})
        available_sizes = list({v.size.name for v in variants if v.size})
        return {
            "type": "options",
            "product_id": product.id,
            "product_name": product.name,
            "available_colors": available_colors,
            "available_sizes": available_sizes,
            "variants_count": len(variants),
        }

    # 2b) If color/size provided, find exact variant 
    q = db.query(ProductVariant).filter(ProductVariant.product_id == product.id)
    if getattr(data, "color", None):
        q = q.join(Color).filter(Color.name.ilike(f"%{data.color.strip()}%"))
    if getattr(data, "size", None):
        q = q.join(Size).filter(Size.name.ilike(f"%{data.size.strip()}%"))
    variant = q.first()
    if variant:
        return {
            "type": "variant",
            "sku": variant.sku,
            "product_id": product.id,
            "product_name": product.name,
            "available_qty": variant.in_stock,
            "price": _decimal_to_float(variant.price),
            "sale_price": _decimal_to_float(variant.sale_price),
            "in_stock": variant.in_stock >= data.quantity
        }

    # 3) Fallback: aggregate all variants
    variants = product.variants
    total_stock = sum(v.in_stock for v in variants) if variants else 0
    prices = [float(v.price) for v in variants if v.price is not None] if variants else []
    return {
        "type": "product_aggregate",
        "product_id": product.id,
        "product_name": product.name,
        "total_available_qty": total_stock,
        "variants_count": len(variants),
        "price_range": {"min": min(prices) if prices else None, "max": max(prices) if prices else None},
        "in_stock": total_stock >= data.quantity
    }