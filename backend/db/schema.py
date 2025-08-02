from pydantic import BaseModel

class Stockrequest(BaseModel):
    productName:str
    quantity: int

class Productresponce(Stockrequest):
    pass

class InvoiceRequest(BaseModel):
    customer_name: str
    customer_contact: str
    customer_address: str
    sku: int
    product_name: str
    quantity_needed: int
    total_price: int

class stockUpdate(BaseModel):
    sku:str
    quantity_needed: int
