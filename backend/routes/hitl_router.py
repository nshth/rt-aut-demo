from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from backend.db.schema import HITLSession, HITLMessage, HumanReplyRequest
from backend.service.session_manager import SessionManager
# from backend.routes.auth import get_current_user

router = APIRouter(prefix="/api/hitl", tags=["Human in the Loop"])

@router.get("/sessions", response_model=List[HITLSession])
async def list_sessions(
    filter: str = "all",
    # current_user: dict = Depends(get_current_user)
):
    sessions = await SessionManager.list_active_sessions()
    if filter != "all":
        sessions = [s for s in sessions if s["status"] == filter]
    return sessions


@router.get("/sessions/{session_id}/history", response_model=List[HITLMessage])
async def get_history(
    session_id: str,
    # current_user: dict = Depends(get_current_user)
):
    history = await SessionManager.get_message_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


@router.post("/sessions/{session_id}/reply")
async def human_reply(session_id: str, body: HumanReplyRequest):
    assigned = await SessionManager.get_assigned_admin(session_id)
    if assigned != "admin1":
        raise HTTPException(status_code=403, detail="Not authorized to reply")
    await SessionManager.append_message(session_id, "human", body.text)
    # optional: send via WA too
    return {"status": "ok"}


@router.post("/sessions/{session_id}/takeover")
async def handle_as_human(session_id: str):
    await SessionManager.assign_human(session_id, "admin1")
    await SessionManager.append_message(
        session_id, "system", "A human operator has taken over this conversation."
    )
    return {"status": "ok", "message": "Session now under human control"}
