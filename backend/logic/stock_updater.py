from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from backend.db.models import Product

def update_product_stock(sku: str, quantity:int, db: Session):
    product = db.query(Product).filter(Product.sku == sku).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{sku}' not found.")

    if product.quantity_available < quantity:
        raise HTTPException(status_code=400, detail=f"Only {product.quantity_available} units left in stock.")

    product.quantity_available -= quantity
    db.commit()

    # Need to update
