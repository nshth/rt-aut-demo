import os
import yagmail
import jwt
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from backend.service.websocket_manager import publish_session_update, publish_counts_update
import asyncio
from backend.service.session_manager import SessionManager

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
MOD_EMAIL = os.getenv("RECIPIENT_EMAIL")
UI_HOST = os.getenv("UI_HOST", "http://localhost:3000")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")

# Global variable to hold the main asyncio event loop
main_event_loop = None

def set_main_event_loop(loop):
    """Sets the main event loop for the application."""
    global main_event_loop
    main_event_loop = loop

class EmailNotificationService:
    
    @staticmethod
    def create_ephemeral_admin_token(session_id: str, ttl_hours: int = 1) -> str:
        """Create short-lived admin token for direct session access"""
        payload = {
            "role": "admin_ephemeral",
            "session_id": session_id,
            "exp": datetime.utcnow() + timedelta(hours=ttl_hours),
            "iat": datetime.utcnow()
        } 
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return token
    
    @staticmethod
    def verify_ephemeral_token(token: str) -> Optional[dict]:
        """Verify ephemeral admin token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("role") == "admin_ephemeral":
                return payload
        except jwt.InvalidTokenError:
            pass
        return None
    
    @staticmethod
    async def send_human_support_notification(
            session_id: str,
            reason: str,
            last_message: str = None,
            customer_number: str = None,
            context: dict = None
        ):
            """Send email notification when human support is needed"""
            
            try:
                # Create ephemeral token for direct access
                ephemeral_token = EmailNotificationService.create_ephemeral_admin_token(session_id)
                jump_link = f"{UI_HOST}/hitl/?token={ephemeral_token}"                
                # Build email content
                subject = f"HITL Alert — Session {session_id} requires human support"
                
                body_parts = [
                    f"🚨 Human support required for session: {session_id}",
                    "",
                    f"**Reason:** {reason}",
                ]
                
                if customer_number:
                    body_parts.append(f"**Customer:** {customer_number}")
                    
                if last_message:
                    body_parts.append(f"**Last message:** {last_message}")
                    
                body_parts.extend([
                    f"**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    "",
                    f"**Direct link:** {jump_link}",
                    "",
                    "This link will expire in 1 hour for security.",
                    "",
                    "Please handle this session as soon as possible."
                ])
                
                body = "\n".join(body_parts)
                
                # Send email
                yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
                yag.send(
                    to=MOD_EMAIL,
                    subject=subject,
                    contents=body
                )
                
                print(f"📧 Email notification sent for session {session_id}")
                
                # Publish WebSocket events
                # IMPORTANT: The status is now set *before* calling this function.
                # This function is now only responsible for the email and websockets.
                await publish_session_update(session_id, "need-human-support", last_message)
                await publish_counts_update()
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to send email notification: {e}")
                return False
        
# NEW ASYNC HELPER
async def _async_notify_and_update_status(subject: str, message: str, context: dict):
    """Internal async function to handle the actual logic."""
    session_id = context.get("session_id")
    from_number = context.get("from_number")

    if not session_id:
        print("❌ Cannot notify human support without a session_id.")
        return

    try:
        # 1. Update the session status FIRST
        await SessionManager.set_session_status(session_id, "need-human-support")
        print(f"✅ Session {session_id} status updated to 'need-human-support'")

        # 2. Call the notification service
        # This will send the email AND publish the WebSocket events
        await EmailNotificationService.send_human_support_notification(
            session_id=session_id,
            reason=subject,
            last_message=message,
            customer_number=from_number
        )
    except Exception as e:
        print(f"❌ Error during async notification process: {e}")


def notify_human(subject: str, message: str, context: dict = None):
    """Safe sync bridge for LangChain tool in async environment"""
    if main_event_loop and main_event_loop.is_running():
        # If the main loop is running, schedule the coroutine to run on it
        # This is thread-safe.
        asyncio.run_coroutine_threadsafe(
            _async_notify_and_update_status(subject, message, context or {}),
            main_event_loop
        )
    else:
        # Fallback for environments where there is no running loop (e.g., a simple script)
        # This will create a new loop, run the task, and close it.
        try:
            asyncio.run(_async_notify_and_update_status(subject, message, context or {}))
        except Exception as e:
            print(f"❌ Error in notify_human fallback: {e}")

# async version
async def notify_human_async(subject: str, message: str, context: dict = None):
    await _async_notify_and_update_status(subject, message, context or {})
