import os
import asyncio
from datetime import datetime
from backend.db.schema import SessionStatus, HITLSession, HITLMessage
import redis.asyncio as redis
import uuid
import json
from backend.db.schema import SessionStatus
from dotenv import load_dotenv

load_dotenv()

UPSTASH_REDIS_HOST = os.getenv("UPSTASH_REDIS_HOST")
UPSTASH_REDIS_PORT = os.getenv("UPSTASH_REDIS_PORT")
UPSTASH_REDIS_PASSWORD = os.getenv("UPSTASH_REDIS_PASSWORD")

r = redis.Redis(
    host=UPSTASH_REDIS_HOST,
    port=int(UPSTASH_REDIS_PORT),
    password=UPSTASH_REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs=None,
    decode_responses=True  # ✅ This fixes the bytes issue!
)

class SessionManager:
    SESSION_TTL = 60 * 60 * 24 * 7  
    
    @staticmethod
    async def get_or_create_session(wa_number: str) -> str:
        clean_number = wa_number.replace("whatsapp:", "").replace("+", "")
        key = f"wa:{clean_number}:session"
        session_id = await r.get(key)
        if session_id:
            return session_id

        session_id = str(uuid.uuid4())
        await r.set(key, session_id, ex=SessionManager.SESSION_TTL)

        # store number for reverse lookup
        await r.set(f"session:{session_id}:number", clean_number, ex=SessionManager.SESSION_TTL)

        await r.set(f"session:{session_id}:history", json.dumps([]), ex=SessionManager.SESSION_TTL)
        return session_id

    
    @staticmethod
    async def set_session_status(session_id: str, status: str):
        key = f"session:{session_id}:status"
        await r.set(key, status, ex=SessionManager.SESSION_TTL)


    @staticmethod
    async def get_session_status(session_id: str) -> str:
        key = f"session:{session_id}:status"
        return await r.get(key) or SessionStatus.AGENT_CONTROL
    

    @staticmethod
    async def update_session_summary(session_id: str, last_message: str = None):
        """Store session summary to make listing fast."""
        status = await SessionManager.get_session_status(session_id)
        customer_number = await r.get(f"session:{session_id}:number") or "unknown"
        summary_key = f"session:{session_id}:summary"

        summary = {
            "session_id": session_id,
            "customer_number": customer_number,
            "status": status,
            "last_message": last_message,
            "updated_at": datetime.utcnow().isoformat()
        }
        await r.set(summary_key, json.dumps(summary), ex=SessionManager.SESSION_TTL)

    @staticmethod
    async def append_message(session_id: str, sender: str, text: str):
        """Append message and update summary."""
        key = f"session:{session_id}:history"
        history_raw = await r.get(key)
        history = json.loads(history_raw) if history_raw else []
        history.append({
            "sender": sender,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })
        await r.set(key, json.dumps(history), ex=SessionManager.SESSION_TTL)

        # Update summary for fast listing
        await SessionManager.update_session_summary(session_id, last_message=text)

    @staticmethod
    async def list_active_sessions() -> list[dict]:
        """Return all session summaries fast."""
        sessions = []

        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match="session:*:summary", count=100)
            if not keys:
                if cursor == 0:
                    break
                continue

            summaries = await r.mget(*keys)
            for s in summaries:
                if s:
                    sessions.append(json.loads(s))

            if cursor == 0:
                break

        # sort by updated_at descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    @staticmethod
    async def get_message_history(session_id: str) -> list[dict]:
        key = f"session:{session_id}:history"
        history_raw = await r.get(key)
        history = json.loads(history_raw) if history_raw else []
        return history
    
    @staticmethod
    async def assign_human(session_id: str, admin_id: str):
        await SessionManager.set_session_status(session_id, "under-human-control")
        await r.set(f"session:{session_id}:admin", admin_id, ex=SessionManager.SESSION_TTL)

    @staticmethod
    async def get_assigned_admin(session_id: str):
        return await r.get(f"session:{session_id}:admin")