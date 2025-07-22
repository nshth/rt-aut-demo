from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.schema import InvoiceRequest
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.post("/create-invoice")
def create_invoice(data: InvoiceRequest, db: Session = Depends(get_db)):
    invoice_id = str(uuid.uuid4()[:8])
    total = data.quantity * data.price
    now = datetime.now(timezone.utc)

    return{
        "customer_name": data.customer_name,
        "customer_contact": data.customer_contact,
        "customer_address": data.customer_address,
        "SKU": data.sku,
        "quantity": data.quantity,
        "unit_price": data.price,
        "total": total
    }
