from sqlalchemy.orm import Session
from backend.db.models import Product
from backend.db.schema import Stockrequest


def get_product_stock_status(data: Stockrequest, db: Session) -> dict:
    """
    Queries the database for a product and returns its stock status.
    This is the central business logic.
    """
    product = db.query(Product).filter(Product.name.ilike(f"%{data.productName.strip()}%")).first()

    if not product:
        return {"error": "Product not found"}
    
    return {
        "sku": product.sku,
        "name": product.name,
        "available": product.quantity_available,
        "price": product.price,
        "in_stock": product.quantity_available >= data.quantity
    }