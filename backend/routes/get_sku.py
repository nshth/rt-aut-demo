from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.models import Product

router = APIRouter()

@router.post('/get_sku')
def get_sku(productName: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name.ilike(f"%{productName.strip()}%")).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "SKU": product.sku
    }