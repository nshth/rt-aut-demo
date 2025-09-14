# test_websocket.py - Test WebSocket connection and events
import asyncio
import websockets
import json
import time

class WebSocketTester:
    def __init__(self, uri="ws://localhost:8000/ws/hitl?token=demo-admin-token-12345"):
        self.uri = uri
        self.websocket = None
        
    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"✅ Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
            
    async def listen(self):
        """Listen for messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                print(f"📥 Received: {json.dumps(data, indent=2)}")
        except websockets.exceptions.ConnectionClosed:
            print("❌ WebSocket connection closed")
        except Exception as e:
            print(f"❌ Error listening: {e}")
            
    async def send_message(self, message):
        """Send message to WebSocket"""
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent: {message}")
        except Exception as e:
            print(f"❌ Error sending: {e}")
            
    async def subscribe_to_session(self, session_id):
        """Subscribe to specific session"""
        await self.send_message({
            "type": "subscribe_session",
            "session_id": session_id
        })
        
    async def ping(self):
        """Send ping"""
        await self.send_message({"type": "ping"})

async def test_websocket_connection():
    """Test basic WebSocket connection"""
    print("🧪 Testing WebSocket Connection...")
    
    tester = WebSocketTester()
    
    if await tester.connect():
        # Start listening in background
        listen_task = asyncio.create_task(tester.listen())
        
        # Wait a bit for initial messages
        await asyncio.sleep(2)
        
        # Test ping
        print("\n🏓 Testing ping...")
        await tester.ping()
        
        # Test session subscription 
        print("\n📋 Testing session subscription...")
        await tester.subscribe_to_session("test-session-123")
        
        # Keep connection alive for a bit
        await asyncio.sleep(5)
        
        # Cancel listening
        listen_task.cancel()
        
        await tester.websocket.close()
        print("✅ WebSocket test completed")
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())