from sqlalchemy.orm import Session
from backend.db.models import Product

def fetch_sku(product_name: str, db: Session):
    product = db.query(Product).filter(Product.name.ilike(f"%{product_name.strip()}%")).first()
    
    if product:
        return {
            "sku": product.sku,
            "Unit_price": product.price
        }
    else:
        return None