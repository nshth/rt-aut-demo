from backend.db.schema import InvoiceToolRequest
import uuid
from datetime import datetime, timezone
from io import BytesIO
from reportlab.pdfgen import canvas

def generate_invoice_pdf(data: InvoiceToolRequest, sku: int):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "INVOICE")

    p.setFont("Helvetica", 12)
    p.drawString(50, 760, f"Name: {data.customer_name}")
    p.drawString(50, 740, f"Contact: {data.customer_contact}")
    p.drawString(50, 720, f"Address: {data.customer_address}")
    p.drawString(50, 700, f"Product: {data.product_name}")
    p.drawString(50, 680, f"SKU: {sku}")
    p.drawString(50, 660, f"Quantity: {data.quantity_needed}")
    p.drawString(50, 640, f"Total: Rs. {data.total_price}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
