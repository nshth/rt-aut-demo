from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.schema import stockUpdate
from backend.db.models import Product

router = APIRouter()

@router.post('/update-stock')
def update_stock(data: stockUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.sku == data.sku).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{data.sku}' not found.")

    if product.quantity_available < data.quantity_needed:
        raise HTTPException(status_code=400, detail=f"Only {product.quantity_available} units left in stock.")

    product.quantity_available -= data.quantity_needed
    db.commit()

    return {
        "message": "Stock updated successfully.",
        "sku": product.sku,
        "product": product.name,
        "remaining_quantity": product.quantity_available
    }
