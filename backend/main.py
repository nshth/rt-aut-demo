from fastapi import FastAPI
from backend.routes import check_stock, give_response
from backend.db import models
from backend.db.database import engine

app = FastAPI()
app.include_router(check_stock.router)
app.include_router(give_response.router)