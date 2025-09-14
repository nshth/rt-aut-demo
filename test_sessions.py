# test_sessions.py - Script to create mock sessions for testing
import asyncio
import json
from backend.service.session_manager import SessionManager
from backend.service.websocket_manager import publish_session_update, publish_counts_update, websocket_manager
import os

async def create_mock_sessions():
    """Create mock sessions for testing"""
    
    # Initialize WebSocket manager
    await websocket_manager.initialize_redis()
    
    # Mock session data
    mock_sessions = [
        {
            "wa_number": "+94771234567",
            "status": "need-human-support", 
            "messages": [
                {"sender": "customer", "text": "I want to cancel my order and get a refund. This is urgent."},
                {"sender": "agent", "text": "I understand your concern. Let me connect you with a human representative."},
                {"sender": "customer", "text": "How long will it take?"}
            ]
        },
        {
            "wa_number": "+94779876543",
            "status": "under-human-control",
            "messages": [
                {"sender": "customer", "text": "Can you check my order status please?"},
                {"sender": "human", "text": "Of course! Let me check that for you right away."},
                {"sender": "human", "text": "Your order #12345 has been shipped and will arrive tomorrow."},
                {"sender": "customer", "text": "Thanks for the help with my order status."}
            ]
        },
        {
            "wa_number": "+94715550123", 
            "status": "under-agent-control",
            "messages": [
                {"sender": "customer", "text": "Do you have the Gaming Chair in blue color?"},
                {"sender": "agent", "text": "Let me check our inventory for you."}
            ]
        },
        {
            "wa_number": "+94768889999",
            "status": "under-agent-control", 
            "messages": [
                {"sender": "customer", "text": "What's the price for 2x HD Monitor 24\"?"},
                {"sender": "agent", "text": "The total for 2 x HD Monitor 24\" would be LKR 49,996.00. Would you like to place the order?"}
            ]
        },
        {
            "wa_number": "+94774445555",
            "status": "need-human-support",
            "messages": [
                {"sender": "customer", "text": "I need to talk to a human please"},
                {"sender": "agent", "text": "I understand. Let me connect you with a human representative."}
            ]
        }
    ]
    
    print("🏗️  Creating mock sessions...")
    
    for i, session_data in enumerate(mock_sessions):
        # Create session
        session_id = await SessionManager.get_or_create_session(session_data["wa_number"])
        
        # Set status
        await SessionManager.set_session_status(session_id, session_data["status"])
        
        # Add messages
        for msg in session_data["messages"]:
            await SessionManager.append_message(session_id, msg["sender"], msg["text"])
        
        # Publish updates
        last_message = session_data["messages"][-1]["text"] if session_data["messages"] else ""
        await publish_session_update(session_id, session_data["status"], last_message)
        
        print(f"✅ Created session {i+1}: {session_id} ({session_data['status']})")
    
    # Update counts
    await publish_counts_update()
    
    print("🎉 Mock sessions created! Check your dashboard.")

if __name__ == "__main__":
    asyncio.run(create_mock_sessions())