from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.schema import Stockrequest
from backend.db.models import Product

router = APIRouter()

@router.post('/check-stock')
def check_stock(data: Stockrequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name.ilike(f"%{data.productName.strip()}%")).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "sku": product.sku,
        "name": product.name,
        "available": product.quantity_available,
        "price": product.price,
        "in_stock": product.quantity_available >= data.quantity
    }

