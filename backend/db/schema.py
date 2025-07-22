from pydantic import BaseModel

class Stockrequest(BaseModel):
    productName:str
    quantity: int

class Productresponce(Stockrequest):
    pass

class InvoiceRequest(BaseModel):
    customer_name: str
    customer_contact: int
    customer_address: str
    sku: str
    quantity: str
    price: int

class Calculatetotal(BaseModel):
    sku: str
    quantity: str
    price: int
