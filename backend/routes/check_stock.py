from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.schema import StockRequest
from backend.logic.stock_checker import get_product_stock_status 

router = APIRouter()

@router.post('/check-stock')
def check_stock(data: StockRequest, db: Session = Depends(get_db)):
    # Call the central logic
    result = get_product_stock_status(data, db)
    
    # Handle the error case for the API
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result