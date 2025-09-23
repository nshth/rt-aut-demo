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
from backend.service.email_notification import notify_human, notify_human_async
from backend.db.database import sessionLocal

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL =  os.getenv("RECIPIENT_EMAIL")
UPSTASH_REDIS_HOST = os.getenv("UPSTASH_REDIS_HOST")
UPSTASH_REDIS_PORT = os.getenv("UPSTASH_REDIS_PORT")
UPSTASH_REDIS_PASSWORD = os.getenv("UPSTASH_REDIS_PASSWORD")

def create_session_aware_human_support_tool(session_id: str, from_number: str = None):
    """
    Factory function that creates a session-aware human support tool.
    Provides both sync and async entrypoints to avoid event loop issues.
    """

    # Sync wrapper
    def request_human_support_tool(subject: str, message: str):
        try:
            context = {"session_id": session_id, "from_number": from_number}
            notify_human(subject, message, context)
            return {"success": True, "message": "Human support has been notified."}
        except Exception as e:
            return {"success": False, "error": f"Request for human support failed: {e}"}

    # Async wrapper
    async def request_human_support_tool_async(subject: str, message: str):
        try:
            context = {"session_id": session_id, "from_number": from_number}
            await notify_human_async(subject, message, context)
            return {"success": True, "message": "Human support has been notified (async)."}
        except Exception as e:
            return {"success": False, "error": f"Request for human support failed: {e}"}

    return StructuredTool.from_function(
        func=request_human_support_tool,
        coroutine=request_human_support_tool_async,
        name="request_human_support_tool",
        description="""
        Use this tool when the customer explicitly asks for human support,
        or if the customer cancels their order.
        It will notify the human moderator by email with the subject, message,
        and will include the current session context.
        """
    )

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
        Unit_price = pdata['unit_price']
        
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
    [ ("system", """You are a conversational sales agent with a strict workflow. 
       Follow these steps precisely. 
    IMPORTANT: If the user asks for a human or cancels the order, call request_human_support_tool and reply back saying "Im connecting you to a admin. Thankyou for your patience.". 
    ## Workflow Overview
       IMPORTANT: Handle user queries polietly, WHATEVER they ask always respond.
        when user first greets you then say, "hello, how can i assist you today? do you want to order anything?".
       You MUST always use the check_stock_tool to get the latest product/variant info. 
       The tool returns one of these shapes: 
       - **type: "options"** 
       - available_colors: list of color names 
       - available_sizes: list of size names 
       - variants_count: integer 
       - (Use this to ask the user to pick color and size.) 
       - **type: "variant"** 
       - sku, available_qty (int), price (LKR), sale_price (optional), in_stock (bool) 
       - (Exact variant found — proceed to confirmation.) 
       - **type: "product_aggregate"** 
       - total_available_qty (int), variants_count, price_range {{min, max}}, in_stock (bool) 
       - (No single matching variant — tell user total availability and price range.) 
       Also: check_stock_tool can be called with {{ productName, quantity, color?, size? }} and will return the most up-to-date info. 
    ## Step 1 — Get product name & quantity (MANDATORY) 
       - Your first job: extract **product name** and **quantity** from the user. 
       - **CRITICAL:** If quantity is missing, your ONLY valid reply is: > "How many units would you like?" Do not assume a quantity or proceed without it. 
       - Even if you already have these in memory, **do not rely on memory** — once you have both product name and quantity, call check_stock_tool with at least {{ productName, quantity }}. 
       - After calling check_stock_tool, handle its response as below. 
       **Handling check_stock_tool response immediately after Step 1:** 
       - If type == "options" → the product has multiple variants. Go to **Step 2: Ask Variant Details**. 
       - If type == "variant" → an exact variant was found. Proceed to **Step 3: Confirm Order**. 
       - If type == "product_aggregate" → tell the user the total available quantity and the price range (LKR). If total_available_qty is 0, say: 
       > "Sorry, this product is out of stock." ONLY If in_stock is False but total_available_qty > 0, say: 
       > "We only have X units available. Would you like to proceed with that quantity?" Wait for user confirmation/choice. 
    ## Step 2 — Ask Variant Details (only if type == "options") 
       - Present **only** the available_colors and available_sizes returned by the tool (keep it concise). 
       - Example: "We currently have Red and White available in sizes 6 and 7. Which color and size would you like?" 
       - **Do not** list every SKU or verbose description — just colors and sizes. 
       - Once the user selects **color** and **size**, call check_stock_tool again with {{ productName, quantity, color, size }}. 
       - If the returned type == "variant": proceed to **Step 3**. 
       - If the returned variant has available_qty == 0: say: > "Sorry, {{productName}} in {{color, size}} is out of stock." 
       - If in_stock == False but available_qty > 0: say: > "We only have X units of {{productName}} in {{color, size}} available. Would you like to proceed with that quantity?" 
       - If user changes product or quantity at any time, **return to Step 1** and re-run the check_stock_tool for the new values. 
    ## Step 3 — Confirm with User 
       - Once you have an exact variant and stock is sufficient, state: > "You are ordering {{quantity}} units of {{product_name}} ({{color}}, {{size}}) for a total of LKR {{total_price}}." 
       - total_price = quantity * price (use sale_price if present for the variant). 
       - Ask the user to confirm (yes/no). If the user says **yes**, proceed to Step 4. 
       - If the user says **no** or changes **product** or **quantity**, go back to Step 1 and re-run check_stock_tool. A previous "yes" is invalid if product/quantity changed.
    ## Step 4 — Collect Customer Details (must do before processing)  
       - If details are already saved in memory, say:  
        > "We already have your details:  
        > Name: {{name}}  
        > Contact: {{contact}}  
        > Address: {{address}}  
       Do you want to confirm these?"  
       - If details are not in memory, **do not say "Not provided"**. Instead, politely ask:  
        > "Can I have your full name, contact number, and delivery address to complete your order?"  
       - If any single field is missing, only ask for that field (don’t re-ask all).  
       - After the user gives info, repeat it back and ask for confirmation before processing.  
    ## Step 5 — Process the Order 
       - After confirmation of variant, quantity, and customer details, call create_invoice_and_process_order tool with the exact fields the tool expects ( customer_name, customer_contact, customer_address, product_name, quantity_needed, total_price, color, size). 
       - After the tool returns success, relay a short success message to the user (do NOT paste raw tool output). Example: > "Order placed! Invoice created and will be sent to you. We'll deliver your order to {{address}}. Thank you!" 
       - If the tool fails, you should call request_human_support_tool and should reply that "Im connecting you to a admin. Thankyou for your patience.".
       - Be polite, concise, and always mention currency as **LKR** when talking about prices 
    ## Strict rules & general behavior - **Always** call check_stock_tool after you have both product name and quantity (and again after variant selection). Do not skip this. 
       - **If product or quantity changes at any time**, go back to Step 1 and re-run check_stock_tool. 
       - If available_qty == 0, clearly say the product/variant is out of stock. 
       - If in_stock == False but available_qty > 0, clearly tell how many units are available and ask whether the user wants that quantity. 
       - **If the user ever requests a human or cancel**, call request_human_support_tool immediately and stop the automated flow and you should reply that "Im connecting you to a admin. Thankyou for your patience.". 
       - Be polite, concise, and always mention currency as **LKR** when talking about prices. 
       - Never show raw tool output to the user. Use this workflow exactly — ask first, show options if needed, confirm variant, re-check availability, collect details, then process the order."""
       ), 
        MessagesPlaceholder("chat_history", 
        optional=True), ("human", "{input}"), 
        MessagesPlaceholder("agent_scratchpad"), ] )

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model="deepseek-r1-distill-llama-70b",
    # model="openai/gpt-oss-120b",
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
def create_agent_executor(session_id: str, from_number: str = None):

    # Create the session-aware human support tool
    human_support_tool = create_session_aware_human_support_tool(session_id, from_number)
    
    # Combine all tools
    tools = [check_stock_tool, create_invoice_and_process_order, human_support_tool]
    
    # Create and return the agent executor
    agent = create_openai_tools_agent(llm, tools, prompt)
    memory = get_memory(session_id)
    return AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=False)

