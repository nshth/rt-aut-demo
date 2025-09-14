# backend/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import check_stock, create_invoice, get_sku, update_stock, whatsapp_webhook, hitl_router
from backend.routes.websocket_router import router as websocket_router
from backend.db import models
from backend.db.database import engine

app = FastAPI(title="HITL Dashboard API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(check_stock.router)
app.include_router(create_invoice.router)
app.include_router(update_stock.router)
app.include_router(get_sku.router)
app.include_router(whatsapp_webhook.router)
app.include_router(hitl_router.router)
app.include_router(websocket_router)

# Serve static files for the HITL dashboard
app.mount("/hitl", StaticFiles(directory="frontend", html=True), name="hitl")

@app.get("/")
async def root():
    return {"message": "HITL Dashboard API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Initialize WebSocket manager on startup
from backend.service.websocket_manager import websocket_manager

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await websocket_manager.initialize_redis()
        print("✅ WebSocket manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize WebSocket manager: {e}")
        
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if websocket_manager.redis:
            await websocket_manager.redis.close()
        print("✅ Redis connections closed")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")