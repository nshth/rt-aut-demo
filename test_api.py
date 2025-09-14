# test_api.py - Test HITL API endpoints
import httpx
import asyncio
import json

class APITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        
    async def test_list_sessions(self):
        """Test listing sessions"""
        print("📋 Testing list sessions...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/hitl/sessions")
            
            if response.status_code == 200:
                sessions = response.json()
                print(f"✅ Found {len(sessions)} sessions")
                
                if sessions:
                    self.session_id = sessions[0]["session_id"]
                    print(f"📝 Using session: {self.session_id}")
                    
                    # Print session details
                    for session in sessions[:3]:  # Show first 3
                        print(f"  - {session['session_id']}: {session.get('status')} ({session.get('customer_number')})")
                
                return sessions
            else:
                print(f"❌ Failed to list sessions: {response.status_code}")
                return []
                
    async def test_session_history(self):
        """Test getting session history"""
        if not self.session_id:
            print("❌ No session ID available")
            return
            
        print(f"\n💬 Testing session history for {self.session_id}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/hitl/sessions/{self.session_id}/history")
            
            if response.status_code == 200:
                history = response.json()
                print(f"✅ Found {len(history)} messages")
                
                # Show last few messages
                for msg in history[-2:]:
                    print(f"  {msg['sender']}: {msg['text'][:50]}...")
                    
                return history
            else:
                print(f"❌ Failed to get history: {response.status_code}")
                return []
                
    async def test_human_reply(self):
        """Test sending human reply"""
        if not self.session_id:
            print("❌ No session ID available") 
            return
            
        print(f"\n💬 Testing human reply to {self.session_id}...")
        
        reply_data = {
            "text": "This is a test reply from the API tester"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/hitl/sessions/{self.session_id}/reply",
                json=reply_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Reply sent: {result}")
                return True
            else:
                print(f"❌ Failed to send reply: {response.status_code} - {response.text}")
                return False
                
    async def test_takeover_session(self):
        """Test taking over a session"""
        if not self.session_id:
            print("❌ No session ID available")
            return
            
        print(f"\n🎯 Testing session takeover for {self.session_id}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/hitl/sessions/{self.session_id}/takeover")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Session taken over: {result}")
                return True
            else:
                print(f"❌ Failed to take over session: {response.status_code} - {response.text}")
                return False
                
    async def test_ephemeral_token(self, token):
        """Test ephemeral token validation"""
        print(f"\n🔐 Testing ephemeral token validation...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/hitl/auth/ephemeral?token={token}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Token valid: {result}")
                return result
            else:
                print(f"❌ Token validation failed: {response.status_code}")
                return None

async def test_whatsapp_webhook():
    """Test WhatsApp webhook endpoint"""
    print("\n📱 Testing WhatsApp webhook...")
    
    webhook_data = {
        "From": "whatsapp:+94771234567",
        "Body": "Test message from API tester"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/whatsapp/webhook",
            data=webhook_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook processed: {result}")
        else:
            print(f"❌ Webhook failed: {response.status_code}")

async def run_api_tests():
    """Run all API tests"""
    print("🧪 HITL API Test Suite")
    print("=" * 40)
    
    tester = APITester()
    
    # Test core HITL endpoints
    sessions = await tester.test_list_sessions()
    
    if sessions:
        await tester.test_session_history()
        await tester.test_human_reply()
        await tester.test_takeover_session()
    
    # Test WhatsApp integration
    await test_whatsapp_webhook()
    
    # Test ephemeral token (create one first)
    print("\n🔐 Creating test ephemeral token...")
    from backend.service.email_notification import EmailNotificationService
    test_token = EmailNotificationService.create_ephemeral_admin_token("test-session")
    await tester.test_ephemeral_token(test_token)
    
    print("\n✅ API tests completed!")

if __name__ == "__main__":
    asyncio.run(run_api_tests())