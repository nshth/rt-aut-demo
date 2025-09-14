import os
import yagmail
import jwt
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from backend.service.websocket_manager import publish_session_update, publish_counts_update

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
MOD_EMAIL = os.getenv("RECIPIENT_EMAIL")
UI_HOST = os.getenv("UI_HOST", "http://localhost:3000")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")

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
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
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
            jump_link = f"{UI_HOST}/hitl/session/{session_id}?token={ephemeral_token}"
            
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
            await publish_session_update(session_id, "need-human-support", last_message)
            await publish_counts_update()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
            return False
    
    @staticmethod
    async def notify_session_taken_over(session_id: str, admin_id: str, customer_number: str = None):
        """Notify when a human takes over a session"""
        try:
            subject = f"Session {session_id} taken over by admin"
            
            body_parts = [
                f"ℹ️ Session taken over: {session_id}",
                f"**Admin:** {admin_id}",
            ]
            
            if customer_number:
                body_parts.append(f"**Customer:** {customer_number}")
                
            body_parts.extend([
                f"**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "",
                "Session is now under human control."
            ])
            
            body = "\n".join(body_parts)
            
            # Send email  
            yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
            yag.send(
                to=MOD_EMAIL,
                subject=subject,
                contents=body
            )
            
            # Publish WebSocket events
            await publish_session_update(session_id, "under-human-control")
            await publish_counts_update()
            
        except Exception as e:
            print(f"❌ Failed to send takeover notification: {e}")

# Update the existing notify_human function to use the new service
async def notify_human(subject: str, message: str, context: dict = None):
    """Updated notify_human function with WebSocket integration"""
    session_id = context.get("session_id") if context else None
    customer_number = context.get("from_number") if context else None
    
    if session_id:
        # Mark session as needing human support
        from backend.service.session_manager import SessionManager
        await SessionManager.set_session_status(session_id, "need-human-support")
        
        # Send notification
        await EmailNotificationService.send_human_support_notification(
            session_id=session_id,
            reason=subject,
            last_message=message,
            customer_number=customer_number,
            context=context
        )