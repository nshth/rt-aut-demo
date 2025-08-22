import sys 
import requests
import yagmail

import os
from dotenv import load_dotenv

from backend.db.schema import Stockrequest, InvoiceToolRequest, stockUpdate

from langchain.memory import ConversationBufferMemory
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_groq import ChatGroq

# Import the logic function and the database session factory
from backend.logic.stock_checker import get_product_stock_status
from backend.logic.fetch_sku import fetch_sku
from backend.logic.invoice_generator import generate_invoice_pdf
from backend.logic.stock_updater import update_product_stock
from backend.db.database import sessionLocal

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = "rashahaneefa0@gmail.com"

@tool
def check_stock_tool(data: Stockrequest) -> dict:
    """
    Checks the stock for a specified quantity of a given product.
    For example, if the user asks for '4 Gaming Chair', the productName should be 'Gaming Chair' and the quantity should be 4.
    """
    # Create a dedicated database session for the tool to use
    db = sessionLocal()
    try:
        result = get_product_stock_status(data, db)
        return result
    finally:
        db.close()

@tool
def create_invoice_and_process_order(data: InvoiceToolRequest) -> str:
    """
    Use this tool AFTER the customer confirms their order.
    It creates an invoice and updates the stock.
    You MUST have the customer's name, contact, address, the product name, quantity, and total price.
    Pass the data as an InvoiceToolRequest object with these fields:
    - customer_name: str
    - customer_contact: str  
    - customer_address: str
    - product_name: str
    - quantity_needed: int
    - total_price: float
    """
    db = sessionLocal()
    try:
        # Fetch SKU using the product name
        sku = fetch_sku(data.product_name, db)
        if not sku: 
            return f"Error: {data.product_name} is not found"

        # Update stock
        update_product_stock(sku, data.quantity_needed, db)

        return "Order successfully processed! The invoice has been sent, and the delivery sheet is updated."

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"An error occurred while processing the order: {str(e)}"
    finally:
        db.close()


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are an intelligent order-taking assistant.
            - Answer every user request politely and shortly. 
            - When they ask about product availability, extract the product name and quantity from their request.
            - Call check_stock_tool with: productName (str) and quantity (int)
            - Prices from check_stock_tool are in LKR - always mention this.
            - After check_stock_tool returns data and if product is available:
                * Calculate total price (price * quantity)
                * Show total price and ask for order confirmation
            - If they don't want to order, handle politely.
            - If they want to order, ask for: full name, contact number, address.
            - Once you have ALL required information (full name, contact number, address), you must call create_invoice_and_process_order with the following:
                * customer_name: str
                * customer_contact: str 
                * customer_address: str
                * product_name: str
                * quantity_needed: int
                * total_price: float
            - Return the exact response from create_invoice_and_process_order tool.
            - IMPORTANT: Always call the appropriate tool - don't generate manual responses when tools should be used!
            - Make sure to collect ALL customer information before calling create_invoice_and_process_order
            """),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model="deepseek-r1-distill-llama-70b",
    temperature=0.5
)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
tools = [check_stock_tool, create_invoice_and_process_order]
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True
)