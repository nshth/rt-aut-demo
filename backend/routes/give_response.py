from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.schema import Stockrequest
from backend.db.models import Product

router = APIRouter()

@router.post("/product-responce")
def product_responce(data: Stockrequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(data.sku == Product.sku)
    

