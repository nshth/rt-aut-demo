# test_email.py - Test email notifications
import asyncio
from backend.service.email_notification import EmailNotificationService, notify_human
from backend.service.websocket_manager import websocket_manager

async def test_email_notification():
    """Test email notification system"""
    print("📧 Testing Email Notification System...")
    
    # Initialize WebSocket manager for pub/sub
    await websocket_manager.initialize_redis()
    
    # Test ephemeral token creation
    print("\n🔐 Testing ephemeral token creation...")
    session_id = "test-session-456"
    token = EmailNotificationService.create_ephemeral_admin_token(session_id)
    print(f"✅ Created ephemeral token: {token[:20]}...")
    
    # Test token validation
    print("\n✅ Testing token validation...")
    payload = EmailNotificationService.verify_ephemeral_token(token)
    if payload:
        print(f"✅ Token valid - Session: {payload.get('session_id')}, Expires: {payload.get('exp')}")
    else:
        print("❌ Token validation failed")
    
    # Test full notification (this will send actual email if configured)
    print("\n📬 Testing full email notification...")
    
    try:
        success = await EmailNotificationService.send_human_support_notification(
            session_id="test-session-789",
            reason="Testing email notification system",
            last_message="This is a test message from the automated test",
            customer_number="+94771234567",
            context={"test": True}
        )
        
        if success:
            print("✅ Email notification sent successfully!")
        else:
            print("❌ Email notification failed")
            
    except Exception as e:
        print(f"❌ Email notification error: {e}")
        print("💡 Make sure email credentials are configured in .env")

async def test_notify_human_integration():
    """Test the integrated notify_human function"""
    print("\n🔗 Testing notify_human integration...")
    
    await websocket_manager.initialize_redis()
    
    try:
        await notify_human(
            subject="Test Integration",
            message="Testing integrated notification system",
            context={
                "session_id": "integration-test-session",
                "from_number": "+94771234567"
            }
        )
        print("✅ Integrated notification test completed")
    except Exception as e:
        print(f"❌ Integration test failed: {e}")

if __name__ == "__main__":
    print("🧪 Email Notification Test Suite")
    print("=" * 40)
    
    # Run tests
    asyncio.run(test_email_notification())
    asyncio.run(test_notify_human_integration())
    
    print("\n✅ Email tests completed!")
    print("💡 Check your email inbox for test messages")
    print("💡 Check Redis for session status updates")
    print("💡 Check WebSocket dashboard for real-time updates")