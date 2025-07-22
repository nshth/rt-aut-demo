from sqlalchemy import Column, Integer, String, Numeric
from backend.db.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    quantity_available = Column(Integer)
    price = Column(Numeric(10, 2))

