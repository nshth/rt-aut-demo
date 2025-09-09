# backend/utils/invoice_generator.py
import uuid
from datetime import datetime
from io import BytesIO
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from typing import Optional

from backend.db.schema import InvoiceToolRequest

company_name = "NICK SriLanka."
logo_path = "nick.png"  # keep logo in project root or provide absolute path

tax_rate = 0.0  # percent as decimal (e.g. 0.05 for 5%)

def _format_currency(val: float) -> str:
    return f"LKR {val:,.2f}"

def generate_invoice_pdf(data: InvoiceToolRequest, SKU: str, Unit_price: float, image_url: Optional[str] = None) -> BytesIO:
    """
    Create a simple invoice PDF and return a BytesIO buffer.
    - data: InvoiceToolRequest (customer + product info)
    - SKU: variant SKU string
    - Unit_price: unit price as float
    - image_url: optional product image URL to include (not downloaded here)
    """
    # Build totals
    qty = getattr(data, "quantity_needed", 1) or 1
    unit_price = float(Unit_price or 0.0)
    total_price = float(getattr(data, "total_price", 0.0) or (unit_price * qty))
    subtotal = total_price
    tax = subtotal * tax_rate
    total_with_tax = subtotal + tax

    invoice_number = uuid.uuid4().hex[:10].upper()
    invoice_date = datetime.now().strftime("%d %B %Y")

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # (612, 792)

    # Header / Company
    y = height - 0.75 * inch
    try:
        p.drawImage(logo_path, 0.6 * inch, y - 36, width=1.0*inch, height=1.0*inch, preserveAspectRatio=True, mask='auto')
    except Exception:
        p.setFont("Helvetica-Bold", 18)
        p.drawString(0.6 * inch, y, company_name)

    p.setFont("Helvetica-Bold", 18)
    p.drawString(1.8 * inch, y, company_name)

    p.setFont("Helvetica-Bold", 28)
    p.drawRightString(width - 0.75 * inch, y, "INVOICE")
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 0.75 * inch, y - 18, f"Invoice No. {invoice_number}")
    p.drawRightString(width - 0.75 * inch, y - 34, invoice_date)

    # Billed To
    y -= 1.1 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(0.75 * inch, y, "BILLED TO:")
    p.setFont("Helvetica", 10)
    p.drawString(0.75 * inch, y - 16, data.customer_name)
    p.drawString(0.75 * inch, y - 32, data.customer_contact)

    addr_y = y - 48
    for line in (data.customer_address or "").split(","):
        p.drawString(0.75 * inch, addr_y, line.strip())
        addr_y -= 12

    # Items table header
    table_y = addr_y - 18
    p.setFont("Helvetica-Bold", 11)
    p.drawString(0.75 * inch, table_y, "Item")
    p.drawString(4.25 * inch, table_y, "Quantity")
    p.drawString(5.5 * inch, table_y, "Unit Price")
    p.drawString(7.0 * inch, table_y, "Total")
    p.line(0.75 * inch, table_y - 4, width - 0.75 * inch, table_y - 4)

    # Item row
    row_y = table_y - 20
    p.setFont("Helvetica", 10)
    item_label = f"{data.product_name} (SKU: {SKU})"
    p.drawString(0.75 * inch, row_y, item_label)
    p.drawRightString(4.9 * inch, row_y, str(qty))
    p.drawRightString(6.5 * inch, row_y, _format_currency(unit_price))
    p.drawRightString(width - 0.75 * inch, row_y, _format_currency(total_price))

    # Totals
    totals_y = row_y - 40
    p.line(4 * inch, totals_y + 10, width - 0.75 * inch, totals_y + 10)
    p.setFont("Helvetica", 10)
    p.drawString(4.5 * inch, totals_y - 4, "Subtotal")
    p.drawRightString(width - 0.75 * inch, totals_y - 4, _format_currency(subtotal))

    p.drawString(4.5 * inch, totals_y - 20, f"Tax ({int(tax_rate * 100)}%)")
    p.drawRightString(width - 0.75 * inch, totals_y - 20, _format_currency(tax))

    p.setFont("Helvetica-Bold", 12)
    p.drawString(4.5 * inch, totals_y - 42, "Total")
    p.drawRightString(width - 0.75 * inch, totals_y - 42, _format_currency(total_with_tax))

    # Footer note
    footer_text = "Thanks for your purchase from NICK."
    p.setFont("Helvetica-Oblique", 10)
    p.drawCentredString(width / 2.0, 0.7 * inch, footer_text)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# quick test block (run file directly)
if __name__ == "__main__":
    from backend.db.schema import InvoiceToolRequest
    demo = InvoiceToolRequest(
        customer_name="Amira Khan",
        customer_contact="+94-789-456-231",
        customer_address="no. 45, orchid lane, colombo 5",
        product_name="Floral Dress",
        quantity_needed=2,
        total_price=246.00
    )
    buf = generate_invoice_pdf(demo, SKU="TESTSKU-001", Unit_price=123.00)
    with open("invoice.pdf", "wb") as f:
        f.write(buf.read())
    print("invoice.pdf generated")
