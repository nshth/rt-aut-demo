import yagmail, os, json

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
MOD_EMAIL = os.getenv("RECIPIENT_EMAIL")

from backend.service.session_manager import SessionManager
from backend.service.websocket_manager import broadcast

def notify_human(subject, message, context=None):
    session_id = context.get("session_id") 
    
    if session_id:
        # update redis
        SessionManager.mark_as_needs_human(session_id)
        # push websocket event
        broadcast("session_status_changed", {
            "session_id": session_id,
            "status": "need-human-support"
        })

    # build jump-to link
    jump_link = f"https://your-ui.com/dashboard/session/{session_id}" if session_id else None
    
    # send email
    yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
    contents = f"""{message}
    
    Jump to session: {jump_link or "N/A"}"""
    yag.send(to=MOD_EMAIL, subject=subject, contents=contents)
