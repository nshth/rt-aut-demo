from pydantic import BaseModel

class Stockrequest(BaseModel):
    sku:str
    quantity: int

