from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from pydantic import BaseModel
from backend.db.schema import HITLSession, HITLMessage, HumanReplyRequest
from backend.service.session_manager import SessionManager
from backend.service.whatsapp_service import send_whatsapp_message
from backend.service.websocket_manager import publish_message_created, publish_session_update, publish_counts_update
from backend.service.email_notification import EmailNotificationService
# from backend.routes.auth import get_current_user

router = APIRouter(prefix="/api/hitl", tags=["Human in the Loop"])

@router.get("/sessions", response_model=List[dict])
async def list_sessions(
    filter: str = "all",
    # current_user: dict = Depends(get_current_user)
):
    """List active sessions with optional filtering"""
    sessions = await SessionManager.list_active_sessions()
    if filter != "all":
        # Map filter names to status values
        filter_map = {
            "under-agent-control": "under-agent-control",
            "under-human-control": "under-human-control", 
            "need-human-support": "need-human-support"
        }
        
        if filter in filter_map:
            sessions = [s for s in sessions if s.get("status") == filter_map[filter]]
    
    return sessions

@router.get("/sessions/{session_id}/history", response_model=List[dict])
async def get_history(
    session_id: str,
    # current_user: dict = Depends(get_current_user)
):
    """Get message history for a session"""
    history = await SessionManager.get_message_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


@router.post("/sessions/{session_id}/takeover")
async def handle_as_human(
    session_id: str,
    admin_id: str = "admin1"
):
    """Take over session and mark it under human control"""
    
    await SessionManager.assign_human(session_id, admin_id)

    system_message = "Our staff will contact you via WhatsApp: +0114785236"
    customer_number = await SessionManager.get_session_customer(session_id)

    await SessionManager.append_message(session_id, "agent", system_message)

    await publish_session_update(session_id, "under-human-control", system_message)
    await publish_message_created(session_id, {
        "sender": "agent",
        "text": system_message,
        "timestamp": SessionManager.get_current_timestamp()
    })
    await publish_counts_update()

    return {"status": "ok", "message": "Session now under human control"}

@router.post("/sessions/{session_id}/reply")
async def reply_as_human(
    session_id: str,
    body: HumanReplyRequest,
    admin_id: str = "admin1"
):
    """Reply as human"""
    
    await SessionManager.assign_human(session_id, admin_id)  

    customer_number = await SessionManager.get_session_customer(session_id)
    
    await send_whatsapp_message(customer_number, body.text)
    await SessionManager.append_message(session_id, "human", body.text)

    message_data = {
        "sender": "human",
        "text": body.text,
        "timestamp": SessionManager.get_current_timestamp()
    }

    await publish_session_update(session_id, "under-human-control", body.text)
    await publish_message_created(session_id, message_data)

    return {"status": "ok", "message": "Human reply sent"}


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status"""
    status = await SessionManager.get_session_status(session_id)
    return {"session_id": session_id, "status": status}

# Ephemeral token endpoint for email jump links
@router.get("/auth/ephemeral")
async def validate_ephemeral_token(token: str = Query(...)):
    """Validate ephemeral admin token from email links"""
    payload = EmailNotificationService.verify_ephemeral_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "valid": True,
        "session_id": payload.get("session_id"),
        "expires_at": payload.get("exp")
    }