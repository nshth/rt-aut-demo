# import requests
# from langchain.tools import tool

# API_URL = "http://127.0.0.1:8000/check-stock"  # your FastAPI backend

# @tool
# def check_stock_tool(productName: str, quantity: int) -> dict:
#     """Check if a given product is in stock with the required quantity."""
#     payload = {"productName": productName, "quantity": quantity}
#     response = requests.post(API_URL, json=payload)

#     if response.status_code != 200:
#         return {"error": response.json().get("detail", "Unknown error")}

#     return response.json()


