from fastapi import FastAPI
from backend.routes import check_stock
from backend.db import models
from backend.db.database import engine

app = FastAPI()
app.include_router(check_stock.router)