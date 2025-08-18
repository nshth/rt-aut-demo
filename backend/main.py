from fastapi import FastAPI
from backend.routes import check_stock, create_invoice, get_sku, update_stock, get_message
from backend.agent import chat_agent
from backend.db import models
from backend.db.database import engine

app = FastAPI()
app.include_router(check_stock.router)
app.include_router(create_invoice.router)
app.include_router(update_stock.router)
app.include_router(get_sku.router)
# app.include_router(get_message.router)


