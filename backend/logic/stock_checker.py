# backend/db/stockchecker.py
from typing import Optional, Dict, Any
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
    - If SKU is provided in productName (or if productName exactly matches a SKU), prefer variant lookup.
    - If color/size provided, try to find the exact variant.
    - Otherwise, aggregate across all variants for that product.
    """
    name_or_sku = data.productName.strip()

    # 1) Try exact SKU match first (fast and deterministic)
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

    # 2) Find product by name (case-insensitive, partial)
    product = db.query(Product).filter(Product.name.ilike(f"%{name_or_sku}%")).first()
    if not product:
        return {"error": "Product not found"}

    # 3) If color or size provided, prefer an exact variant match
    if (getattr(data, "color", None) or getattr(data, "size", None)):
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

    # 4) Fallback: aggregate over all variants of the product
    variants = product.variants  # via relationship
    total_stock = sum(v.in_stock for v in variants) if variants else 0
    min_price = None
    max_price = None
    if variants:
        prices = [float(v.price) for v in variants if v.price is not None]
        if prices:
            min_price, max_price = min(prices), max(prices)

    return {
        "type": "product_aggregate",
        "product_id": product.id,
        "product_name": product.name,
        "total_available_qty": total_stock,
        "variants_count": len(variants),
        "price_range": {"min": min_price, "max": max_price},
        "in_stock": total_stock >= data.quantity
    }
