import uuid
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from backend.db.schema import InvoiceToolRequest

company_name = "NICK SriLanka."
logo_path = "nick.png"
invoice_number = "demo1"
invoice_date = datetime.now().strftime("%d %B %Y")
payment_info = "Cash On delivery"
tax_rate = 0.0
tax = 0.0

def generate_invoice_pdf(data: InvoiceToolRequest, SKU: str, Unit_price: int):
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  #(612, 792)

    # --- Colors ---
    light_grey = colors.HexColor("#F0F0F0")
    dark_grey = colors.HexColor("#333333")
    
    # --- Page Background ---
    p.setFillColor(dark_grey)

    # --- Header Section ---
    y_pos = height - 1 * inch
    
    # Company Logo & Name (Left side)
    try:
        # Increased logo size
        p.drawImage(logo_path, 0.75 * inch, y_pos - 30, width=1.2*inch, height=1.2*inch, preserveAspectRatio=True, mask='auto')
    except IOError:
        # Fallback to text if image not found
        p.setFont("Helvetica-Bold", 40)
        p.drawString(0.75 * inch, y_pos, "NICK SriLanka.")

    # Company name under logo
    p.setFont("Helvetica-Bold", 14)
    p.drawString(0.75 * inch, y_pos - 40, company_name)

    # Invoice Title (Right side, aligned better)
    p.setFont("Helvetica-Bold", 32)
    p.drawRightString(width - 0.75 * inch, y_pos, "INVOICE")

    p.setFont("Helvetica", 12)
    p.drawRightString(width - 0.75 * inch, y_pos - 20, f"Invoice No. {invoice_number}")
    p.drawRightString(width - 0.75 * inch, y_pos - 35, f"{invoice_date}")

    # --- Billed To Section ---
    y_pos -= 1.6 * inch
    p.setFont("Helvetica-Bold", 14)
    p.drawString(0.75 * inch, y_pos, "BILLED TO:")
    p.setFont("Helvetica", 12)
    p.drawString(0.75 * inch, y_pos - 15, data.customer_name)
    p.drawString(0.75 * inch, y_pos - 30, data.customer_contact)
    # Handle multi-line address
    address_lines = data.customer_address.split(', ')
    addr_y = y_pos - 45
    for line in address_lines:
        p.drawString(0.75 * inch, addr_y, line)
        addr_y -= 15

    # --- Items Table ---
    y_pos -= 1.5 * inch
    table_x_positions = {
        "item": 0.75 * inch,
        "quantity": 4.25 * inch,
        "unit_price": 5.5 * inch,
        "total": 7 * inch
    }

    # Table Header
    p.setFont("Helvetica-Bold", 12)
    p.drawString(table_x_positions["item"], y_pos, "Item")
    p.drawString(table_x_positions["quantity"], y_pos, "Quantity")
    p.drawString(table_x_positions["unit_price"], y_pos, "Unit Price")
    p.drawString(table_x_positions["total"], y_pos, "Total")
    
    # Header line
    y_pos -= 10
    p.line(0.75 * inch, y_pos, width - 0.75 * inch, y_pos)
    y_pos -= 15
    
    # Table Row (aligned neatly)
    p.setFont("Helvetica", 12)
    p.drawString(table_x_positions["item"], y_pos, data.product_name)
    p.drawRightString(table_x_positions["quantity"] + 40, y_pos, str(data.quantity_needed))
    p.drawRightString(table_x_positions["unit_price"] + 40, y_pos, f"LKR {Unit_price:.2f}")
    p.drawRightString(table_x_positions["total"] + 40, y_pos, f"LKR {data.total_price:.2f}")

    # --- Totals Section ---
    y_pos -= 40
    p.line(4 * inch, y_pos, width - 0.75 * inch, y_pos)
    y_pos -= 15

    totals_y_base = y_pos
    p.setFont("Helvetica", 12)
    p.drawString(4.5 * inch, totals_y_base - 20, "Subtotal")
    p.drawRightString(width - 0.75 * inch, totals_y_base - 20, f"LKR {data.total_price:.2f}")

    p.drawString(4.5 * inch, totals_y_base - 40, f"Tax ({int(tax_rate * 100)}%)")
    p.drawRightString(width - 0.75 * inch, totals_y_base - 40, f"LKR {tax:.2f}")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(4.5 * inch, totals_y_base - 70, "Total")
    p.drawRightString(width - 0.75 * inch, totals_y_base - 70, f"LKR {data.total_price:.2f}")

    # --- Footer Section ---
    footer_y = 2.5 * inch
    p.setFont("Helvetica-Bold", 14)
    p.drawString(footer_y, footer_y, "Thanks For your Purchase from NICK.")



    # --- Save PDF ---
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# --- Main execution block ---
if __name__ == '__main__':
    invoice_details = InvoiceToolRequest(
        customer_name="Amira Khan",
        customer_contact="+94-789-456-231",
        customer_address="no. 45, orchid lane, colombo 5",
        product_name="Floral Dress",
        quantity_needed=2,
        total_price=246.00
    )

    # Generate the PDF
    pdf_buffer = generate_invoice_pdf(invoice_details, SKU=104, Unit_price=150.00)

    # Save the PDF to a file
    with open("invoice.pdf", "wb") as f:
        f.write(pdf_buffer.read())

    print("Successfully generated invoice.pdf")
