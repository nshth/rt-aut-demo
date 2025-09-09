#Every task is new agent excecute with chat history
#  so the agent exactly know what to respond
import yagmail

import os
from dotenv import load_dotenv

from backend.db.schema import StockRequest, InvoiceToolRequest, StockUpdate

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_groq import ChatGroq

from backend.logic.stock_checker import get_product_stock_status
from backend.logic.fetch_sku import fetch_sku
from backend.logic.invoice_generator import generate_invoice_pdf
from backend.logic.stock_updater import update_product_stock
from backend.logic.del_sheet_maker import make_delivery_sheet
from backend.service.hitl import notify_human
from backend.db.database import sessionLocal

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL =  os.getenv("RECIPIENT_EMAIL")
UPSTASH_REDIS_HOST = os.getenv("UPSTASH_REDIS_HOST")
UPSTASH_REDIS_PORT = os.getenv("UPSTASH_REDIS_PORT")
UPSTASH_REDIS_PASSWORD = os.getenv("UPSTASH_REDIS_PASSWORD")

def request_human_support_tool(subject: str, message: str, context: dict = None):
    try:
        notify_human(subject, message, context)
        return {"success": True, "message": "Human support has been notified."}
    except Exception as e:
        return {"success": False, "error": f"Request for human support failed: {e}"}

request_human_support_tool = StructuredTool.from_function(
    func=request_human_support_tool,
    name="request_human_support_tool",
    description="""
    Use this tool when the customer explicitly asks for human support,
    or if customer cancells their order.
    It will notify the human moderator by email with the subject, message,
    and any optional context.
    """)

def check_stock_tool(data: StockRequest) -> dict:
    # Create a dedicated database session for the tool to use
    db = sessionLocal()
    try:
        result = get_product_stock_status(data, db)
        return result
    finally:
        db.close()

check_stock_tool = StructuredTool.from_function(
    func=check_stock_tool,
    name="check_stock_tool",
    description="""
    Checks the stock for a specified quantity of a given product.
    For example, if the user asks for '4 Gaming Chair', the productName should be 'Gaming Chair' and the quantity should be 4.
    """
)

def create_invoice_and_process_order(data: InvoiceToolRequest) -> dict:
    db = sessionLocal()
    try:
        # Fetch SKU using the product name
        pdata = fetch_sku(data.product_name, db)
        if not pdata: 
            return f"Error: {data.product_name} is not found"
        
        sku = pdata['sku']
        Unit_price = pdata['Unit_price']
        
        # Make PFD
        pdf_buffer = generate_invoice_pdf(data, sku, Unit_price)

        pdf_path = f"{data.customer_name}_invoice.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.read())
    
        #send it to company email but had to send it to customer via whatsapp
        try:
            yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
            yag.send(
                to=RECIPIENT_EMAIL,
                subject=f"New Order Invoice - {data.customer_name}",
                contents=(
                    f"Hello Team,\n\n"
                    f"A new order has been placed.\n\n"
                    f"Customer: {data.customer_name}\n"
                    f"Contact: {data.customer_contact}\n"
                    f"Address: {data.customer_address}\n"
                    f"Product: {data.product_name} (x{data.quantity_needed})\n"
                    f"Total Price: LKR {data.total_price}\n\n"
                    "Please find the invoice attached."
                ),
                attachments=[pdf_path]
            )
        except Exception as e:
            return f"Invoice saved locally, but email failed: {e}"

        make_delivery_sheet(data)

        # update_product_stock(sku, data.quantity_needed, db)

        return {
            "success": True,
            "message": f"Thank you {data.customer_name}, your order for {data.quantity_needed} x {data.product_name} has been confirmed. Our delivery team will contact you shortly.",
            "customer_name": data.customer_name,
            "product": data.product_name,
            "quantity": data.quantity_needed,
            "total_price": data.total_price
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"success": False, "error": f"An error occurred while processing the order: {str(e)}"}
    finally:
        db.close()

create_invoice_and_process_order = StructuredTool.from_function(
    func=create_invoice_and_process_order,
    name="create_invoice_and_process_order",
    description="""
    Use this tool AFTER the customer confirms their order.
    It append the data to google sheet.
    You MUST have the customer's name, contact, address, the product name, quantity, and total price.
    Pass the data as an InvoiceToolRequest object with these fields:
    - customer_name: str
    - customer_contact: str  
    - customer_address: str
    - product_name: str
    - quantity_needed: int
    - total_price: float
    """
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a conversational sales agent with a strict workflow. Follow these steps precisely.

            ## Workflow Steps
            **if customer ever wants to talk to a human or cancells their order then call `request_human_support_tool`**

            **Step 1: Get Product and Quantity**
            - Your first job is to identify the product name and quantity from the user's request, if not ask.
            - Even if you have this details in memory dont use it but call `check_stock_tool` with the provided information to get most Up to date details about product.
            - **CRITICAL RULE:** If the user asks for a product but does NOT specify a quantity, you MUST ask for it. Do NOT assume a quantity. Your ONLY valid action is to ask "How many units would you like?".
            - Once you have both the product name and a specific quantity, immediately use the `check_stock_tool` to check availability and get the price.
            - if the "available" is 0, say its not in stock but if availble is greater than 0 but you got 'in_stock': False, then mention how much is availble to the user. 
            - If the user is satisfied with the available quantity, then move to step 2.
         
            **Step 2: Confirm with User**
            - If the product is in stock, state the product name, quantity, and the TOTAL price (quantity * price). Always mention the currency is LKR.
            - Ask the user for a clear confirmation to proceed with the order. Example: "The total for 2 x HD Monitor 24" is 24,998.00 LKR. Would you like to place the order?"
            - If the customer didnt want to confirm, handle it politely. dont ask the confirmation again.
            - If the user changes the product or quantity at ANY time (even after saying 'yes'), you MUST return to Step 1.
            - This means: always call `check_stock_tool` again to re-check availability and update the price for the new quantity.
            - A previous 'yes' confirmation is invalid if the product or quantity changes. Treat it as a fresh request.
                        
            **Step 3: Collect Customer Details**
            - **CRITICAL:** Once the user confirms the order, you MUST transition to this step.
            - if you already have the customer details in memory, ask the user to have that as their details to confirm the order. Example: "We already have your details, Name: customer_name, Contact: customer_contact, Address: customer_address. Do you want to confirm this as your details?"
            - if customer agreed with this as their details, use this to move to next step. but if they change even one detail, change it and confirm the details to the user before moving to the next step.
            - if you dont have any details in memory then Your action is to ask for the customer's full name, contact number, and delivery address. If they missed to give any details, ask for the specific missing details.
         
            **Step 4: Process the Order**
            - Once you have the full name, contact number, AND address, call the `create_invoice_and_process_order` tool.
            - Pass all the required arguments correctly. If customer missed to give a details, ask them to give it.
            - After the tool call is successful, replay the success message from the tool's response to the user.

            ## General Rules:
            - **if customer ever wants to talk to a human or cancells their order then call `request_human_support_tool`**
            - Be polite and concise.
            - Never show raw tool output.
            - Once the order is confirmed, you must move forward with calling the `create_invoice_and_process_order`.
            """),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model="deepseek-r1-distill-llama-70b",
    temperature=0.2 
)

def get_memory(session_id: str):
    redis_url = f"rediss://:{UPSTASH_REDIS_PASSWORD}@{UPSTASH_REDIS_HOST}:{UPSTASH_REDIS_PORT}"
    chat_history = RedisChatMessageHistory(
        session_id=session_id,
        url=redis_url
    )
    return ConversationBufferMemory(
        memory_key="chat_history",  
        input_key="input",
        chat_memory=chat_history,
        return_messages=True
    )

tools = [check_stock_tool, create_invoice_and_process_order, request_human_support_tool]
agent = create_openai_tools_agent(llm, tools, prompt)
