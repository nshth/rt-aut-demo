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
    sku: str
    product_name: str
    quantity_needed: int
    total_price: float

class stockUpdate(BaseModel):
    sku:str
    quantity_needed: int

class ChatRequest(BaseModel):
    sessionId: str
    message: str

class InvoiceToolRequest(BaseModel):
    customer_name: str
    customer_contact: str
    customer_address: str
    product_name: str
    quantity_needed: int
    total_price: float