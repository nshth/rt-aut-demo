from sqlalchemy.orm import Session
from backend.db.models import Product

def fetch_sku(product_name: str, db: Session) -> str | None:
    product = db.query(Product).filter(Product.name.ilike(f"%{product_name.strip()}%")).first()
    
    return product.sku if product else None