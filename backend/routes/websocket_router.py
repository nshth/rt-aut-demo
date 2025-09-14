import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from backend.service.websocket_manager import websocket_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple JWT verification (you should use proper JWT validation)
def verify_admin_token(token: str) -> bool:
    """Verify admin JWT token - implement proper JWT validation"""
    # Placeholder - implement proper JWT verification
    return token and len(token) > 10

@router.websocket("/ws/hitl")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for HITL dashboard"""
    
    # Verify admin token
    if not verify_admin_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return
        
    connection_id = str(uuid.uuid4())
    
    try:
        # Initialize Redis if not done
        if not websocket_manager.redis:
            await websocket_manager.initialize_redis()
            
        # Accept connection
        await websocket_manager.connect(websocket, connection_id)
        
        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_client_message(connection_id, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {connection_id}")
            except Exception as e:
                logger.error(f"Error handling message from {connection_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)

async def handle_client_message(connection_id: str, message: dict):
    """Handle messages from WebSocket clients"""
    message_type = message.get("type")
    
    if message_type == "subscribe_session":
        session_id = message.get("session_id")
        if session_id:
            await websocket_manager.subscribe_to_session(connection_id, session_id)
            
    elif message_type == "unsubscribe_session":
        session_id = message.get("session_id") 
        if session_id:
            await websocket_manager.unsubscribe_from_session(connection_id, session_id)
            
    elif message_type == "ping":
        # Send pong back
        websocket = websocket_manager.active_connections.get(connection_id)
        if websocket:
            await websocket.send_text(json.dumps({"type": "pong"}))