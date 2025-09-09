# backend/db/fetch_sku.py
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from decimal import Decimal

from backend.db.models import Product, ProductVariant

def _decimal_to_float(d: Optional[Decimal]) -> Optional[float]:
    if d is None:
        return None
    return float(d)

def fetch_sku(product_name_or_sku: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Find a SKU and unit price.
    Behavior:
      1. If input exactly matches a variant SKU, return that variant.
      2. Otherwise, try to find a product by name (case-insensitive).
         - Prefer an in-stock variant (highest stock).
         - Otherwise return the cheapest variant available.
    Returns dict with keys: sku, unit_price, product_name, variant_id
    or None if nothing is found.
    """
    key = product_name_or_sku.strip()
    if not key:
        return None

    # 1) Try exact SKU match
    variant = db.query(ProductVariant).filter(ProductVariant.sku == key).first()
    if variant:
        return {
            "variant_id": variant.id,
            "sku": variant.sku,
            "unit_price": _decimal_to_float(variant.price),
            "product_name": variant.product.name if variant.product else None,
            "in_stock": variant.in_stock
        }

    # 2) Find product by name (partial, case-insensitive)
    product = db.query(Product).filter(Product.name.ilike(f"%{key}%")).first()
    if not product:
        return None

    # Try to find the best variant:
    # prefer in_stock > 0 ordered by in_stock desc
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.product_id == product.id, ProductVariant.in_stock > 0)
        .order_by(desc(ProductVariant.in_stock))
        .first()
    )

    # if no in-stock variant, pick the cheapest variant (by price asc)
    if not variant:
        variant = (
            db.query(ProductVariant)
            .filter(ProductVariant.product_id == product.id)
            .order_by(asc(ProductVariant.price))
            .first()
        )

    if not variant:
        return None

    return {
        "variant_id": variant.id,
        "sku": variant.sku,
        "unit_price": _decimal_to_float(variant.price),
        "product_name": product.name,
        "in_stock": variant.in_stock
    }
