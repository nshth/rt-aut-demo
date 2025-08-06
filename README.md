# rt-aut-demo - AI-Powered Order Assistant

P03 is an intelligent order-taking assistant designed to automate the messy manual process of handling orders from social commerce platforms like WhatsApp and Facebook. Built using LLMs, n8n, and a custom FastAPI backend, it handles customer queries, updates stock, generates invoices, and manages deliveries.


## Features

- **AI Chat Widget**  
  Uses a custom-trained LLM to interact with customers and understand orders.

- **Product Availability Check**  
  Queries a connected PostgreSQL database to verify product SKUs and quantities in real-time.

- **Order Confirmation Flow**  
  Summarizes and confirms orders with the customer before proceeding.

- **Dynamic Pricing + Delivery Fees**  
  Calculates total price including delivery (based on location/weight logic).

- **Invoice Generation**  
  Automatically creates and sends an invoice if the customer confirms the order.

- **n8n Workflow Orchestration**  
  Orchestrates everything — from AI responses to DB updates, invoice creation, and adding to delivery sheets.


## How It Works (Simplified Flow)

1. Customer sends a message via chat widget. 
2. LLM parses the intent and extracts product/order info.
3. FastAPI fetches SKU & price data → confirms stock.
4. Order total + delivery fee is calculated.
5. If confirmed, an invoice is generated & sent. 
6. Order is added to delivery sheet & stock is updated.