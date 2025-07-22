from backend.db.database import sessionLocal, DB_URL
from backend.db.models import Product

products = [
    {"sku": "101", "name": "Wireless Mouse", "quantity_available": 15, "price": 1999.99},
    {"sku": "102", "name": "Mechanical Keyboard", "quantity_available": 8, "price": 4999.50},
    {"sku": "103", "name": "HD Monitor 24", "quantity_available": 4, "price": 12499.00},
    {"sku": "104", "name": "USB-C Cable 1m", "quantity_available": 40, "price": 499.00},
    {"sku": "105", "name": "Bluetooth Speaker", "quantity_available": 10, "price": 3499.75},
    {"sku": "106", "name": "Laptop Stand", "quantity_available": 20, "price": 2499.00},
    {"sku": "107", "name": "Webcam HD 1080p", "quantity_available": 5, "price": 2999.99},
    {"sku": "108", "name": "Portable SSD 1TB", "quantity_available": 7, "price": 8499.25},
    {"sku": "109", "name": "Wireless Earbuds", "quantity_available": 12, "price": 3999.00},
    {"sku": "110", "name": "Gaming Chair", "quantity_available": 2, "price": 14999.99}
]

db = sessionLocal()

for p in products:
    exists = db.query(Product).filter_by(sku=p['sku']).first()
    if not exists:
        product = Product(**p)
        print("Using DB URL:", DB_URL)
        db.add(product)

db.commit()
db.close()

print("done")