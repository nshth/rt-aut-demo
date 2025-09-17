import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

UPSTASH_REDIS_PASSWORD = os.getenv('UPSTASH_REDIS_PASSWORD')
UPSTASH_REDIS_HOST = os.getenv('UPSTASH_REDIS_HOST')
UPSTASH_REDIS_PORT = os.getenv('UPSTASH_REDIS_PORT')

r = redis.Redis(
    host=UPSTASH_REDIS_HOST,
    port=int(UPSTASH_REDIS_PORT),
    password=UPSTASH_REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs=None,
    decode_responses=True
)

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_subscriptions: Dict[str, Set[str]] = {}  # session_id -> set of connection_ids
        self.global_subscribers: Set[str] = set()
        self.redis = None
        self.pubsub = None
        
    async def initialize_redis(self):
        """Initialize Redis connection and pubsub"""
        self.redis = r
        self.pubsub = self.redis.pubsub()
        
        # Subscribe to global channel
        await self.pubsub.subscribe("hitl:global")
        
        # Start pubsub listener
        asyncio.create_task(self._pubsub_listener())
        
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.global_subscribers.add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # Send initial counts
        await self._send_current_counts(connection_id)
        
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnect"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
        if connection_id in self.global_subscribers:
            self.global_subscribers.remove(connection_id)
            
        # Remove from session subscriptions
        for session_id, subscribers in self.session_subscriptions.items():
            subscribers.discard(connection_id)
            
        logger.info(f"WebSocket disconnected: {connection_id}")
        
    async def subscribe_to_session(self, connection_id: str, session_id: str):
        """Subscribe connection to specific session updates"""
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()
            # Subscribe to Redis channel for this session
            await self.pubsub.subscribe(f"hitl:session:{session_id}")
            
        self.session_subscriptions[session_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to session {session_id}")
        
    async def unsubscribe_from_session(self, connection_id: str, session_id: str):
        """Unsubscribe connection from session updates"""
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(connection_id)
            
            # If no more subscribers, unsubscribe from Redis
            if not self.session_subscriptions[session_id]:
                await self.pubsub.unsubscribe(f"hitl:session:{session_id}")
                del self.session_subscriptions[session_id]
                
        logger.info(f"Connection {connection_id} unsubscribed from session {session_id}")
        
    async def _pubsub_listener(self):
        """Listen for Redis pubsub messages and relay to WebSocket clients"""
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message and message['data']:
                    channel = message['channel']
                    
                    # FIX: Handle bytes properly
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')
                        
                    if isinstance(message['data'], bytes):
                        data = json.loads(message['data'].decode('utf-8'))
                    else:
                        data = json.loads(message['data'])
                    
                    if channel == "hitl:global":
                        await self._broadcast_to_global(data)
                    elif channel.startswith("hitl:session:"):
                        session_id = channel.replace("hitl:session:", "")
                        await self._broadcast_to_session(session_id, data)
                        
            except Exception as e:
                logger.error(f"Error in pubsub listener: {e}")
                await asyncio.sleep(1)
                
    async def _broadcast_to_global(self, data: dict):
        """Broadcast message to all global subscribers"""
        if not self.global_subscribers:
            return
            
        disconnected = []
        for connection_id in self.global_subscribers:
            try:
                websocket = self.active_connections.get(connection_id)
                if websocket:
                    await websocket.send_text(json.dumps(data))
                else:
                    disconnected.append(connection_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
                
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
            
    async def _broadcast_to_session(self, session_id: str, data: dict):
        """Broadcast message to session subscribers"""
        subscribers = self.session_subscriptions.get(session_id, set())
        if not subscribers:
            return
            
        disconnected = []
        for connection_id in subscribers:
            try:
                websocket = self.active_connections.get(connection_id)
                if websocket:
                    await websocket.send_text(json.dumps(data))
                else:
                    disconnected.append(connection_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
                
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
            
    async def _send_current_counts(self, connection_id: str):
        """Send current session counts to a connection"""
        try:
            from backend.service.session_manager import SessionManager
            sessions = await SessionManager.list_active_sessions()
            
            counts = {
                "all": len(sessions),
                "agent_control": len([s for s in sessions if s.get("status") == "under-agent-control"]),
                "human_control": len([s for s in sessions if s.get("status") == "under-human-control"]),
                "need_human_support": len([s for s in sessions if s.get("status") == "need-human-support"])
            }
            
            message = {
                "type": "sessions:counts",
                "counts": counts
            }
            
            websocket = self.active_connections.get(connection_id)
            if websocket:
                await websocket.send_text(json.dumps(message))
                
        except Exception as e:
            logger.error(f"Error sending counts to {connection_id}: {e}")

# Global instance
websocket_manager = WebSocketManager()

# Utility functions for publishing events
async def publish_session_update(session_id: str, status: str, last_message: str = None):
    """Publish session update event"""
    if not websocket_manager.redis:
        return
        
    event = {
        "type": "session:update",
        "session_id": session_id,
        "status": status,
        "last_updated": int(datetime.utcnow().timestamp()),
        "preview": last_message
    }
    
    # Publish to both global and session-specific channels
    await websocket_manager.redis.publish("hitl:global", json.dumps(event))
    await websocket_manager.redis.publish(f"hitl:session:{session_id}", json.dumps(event))
    
async def publish_message_created(session_id: str, message: dict):
    """Publish new message event"""
    if not websocket_manager.redis:
        return
        
    event = {
        "type": "message:created",
        "session_id": session_id,
        "message": message
    }
    
    await websocket_manager.redis.publish(f"hitl:session:{session_id}", json.dumps(event))
    
async def publish_counts_update():
    """Publish updated session counts"""
    if not websocket_manager.redis:
        return
        
    try:
        from backend.service.session_manager import SessionManager
        sessions = await SessionManager.list_active_sessions()
        
        counts = {
            "all": len(sessions),
            "agent_control": len([s for s in sessions if s.get("status") == "under-agent-control"]),
            "human_control": len([s for s in sessions if s.get("status") == "under-human-control"]), 
            "need_human_support": len([s for s in sessions if s.get("status") == "need-human-support"])
        }
        
        event = {
            "type": "sessions:counts",
            "counts": counts
        }
        
        await websocket_manager.redis.publish("hitl:global", json.dumps(event))
        
    except Exception as e:
        logger.error(f"Error publishing counts update: {e}")

# Backward compatibility function
def broadcast(event_type: str, data: dict):
    """Synchronous wrapper for backward compatibility"""
    asyncio.create_task(publish_session_update(
        data.get("session_id", ""),
        data.get("status", ""),
        data.get("preview", "")
    ))