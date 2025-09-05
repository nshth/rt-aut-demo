import os
import asyncio
import redis.asyncio as redis
import uuid
import json
from backend.agent.chat_agent import get_memory
from langchain.memory import ConversationBufferMemory
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
        # Clean the number
        clean_number = wa_number.replace("whatsapp:", "").replace("+", "")
        
        # Get existing session
        key = f"wa:{clean_number}:session"
        session_id = await r.get(key)
        
        if session_id:
            # With decode_responses=True, this will already be a string
            return session_id

        # Create new session
        session_id = str(uuid.uuid4())
        await r.set(key, session_id, ex=SessionManager.SESSION_TTL)
        
        # Initialize empty history (optional, but good practice)
        history_key = f"session:{session_id}:history"
        await r.set(history_key, json.dumps([]), ex=SessionManager.SESSION_TTL)
        
        return session_id