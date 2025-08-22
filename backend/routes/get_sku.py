from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.models import Product

router = APIRouter()

@router.post('/get_sku')
def get_sku(productName: str, db: Session = Depends(get_db)) -> str | None:
    product = db.query(Product).filter(Product.name.ilike(f"%{productName.strip()}%")).first()
    
    return product.sku if product else None
