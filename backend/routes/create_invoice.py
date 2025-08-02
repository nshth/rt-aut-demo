from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.db.database import sessionLocal, get_db
from backend.db.schema import InvoiceRequest
import uuid
from datetime import datetime, timezone
from io import BytesIO
from reportlab.pdfgen import canvas

router = APIRouter()
@router.post("/create-invoice")
def generate_invoice(data: InvoiceRequest):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "INVOICE")

    p.setFont("Helvetica", 12)
    p.drawString(50, 760, f"Name: {data.customer_name}")
    p.drawString(50, 740, f"Contact: {data.customer_contact}")
    p.drawString(50, 720, f"Address: {data.customer_address}")
    p.drawString(50, 700, f"Product: {data.product_name}")
    p.drawString(50, 680, f"SKU: {data.sku}")
    p.drawString(50, 660, f"Quantity: {data.quantity_needed}")
    p.drawString(50, 640, f"Total: Rs. {data.total_price:.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice.pdf"}
    )

# add date and time
# add uuid