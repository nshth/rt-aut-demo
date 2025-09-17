# twilio send logic is comment out to test 
import asyncio
import os
from dotenv import load_dotenv
import httpx
from backend.service.session_manager import SessionManager
from langchain.agents import AgentExecutor
from backend.agent.chat_agent import create_agent_executor
from backend.service.email_notification import notify_human_async
from backend.service.websocket_manager import publish_message_created, publish_session_update, publish_counts_update

load_dotenv()
session_manager = SessionManager()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") 
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")

def _wa(n: str) -> str:
    n = n.strip()
    return n if n.startswith("whatsapp:") else f"whatsapp:{n}"

async def send_whatsapp_message(to_number: str, message: str) -> None:
    """Send WhatsApp message via Twilio API"""
    return (message)
    # print(f"Agent reply:{message}")
    # url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    # data = {
    #     "From": _wa(TWILIO_WHATSAPP_NUMBER),
    #     "To": _wa(to_number),
    #     "Body": message,
    # }
    
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(
    #         url, 
    #         data=data, 
    #         auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), 
    #         timeout=30
    #     )
    #     try:
    #         resp.raise_for_status()
    #     except httpx.HTTPStatusError as e:
    #         detail = resp.text[:500]
    #         raise RuntimeError(f"Twilio send failed: {e} :: {detail}") from e

async def process_whatsapp_message(from_number: str, message: str) -> dict:
    """Process a single WhatsApp message using LangChain agent"""
    session_id = None
    try:
        session_id = await session_manager.get_or_create_session(from_number)
        
        # Add customer message to history and publish via WebSocket
        customer_message = await SessionManager.append_message(session_id, "customer", message)
        await publish_message_created(session_id, customer_message)
        
        # Check if session is under human control
        status = await SessionManager.get_session_status(session_id)
        if status == "under-human-control":
            # Don't process with agent, just notify that human should respond
            return {
                "status": "under_human_control",
                "session_id": session_id,
                "message": "Session is under human control",
                "from_number": from_number
            }

        # Process with agent
        agent_executor = create_agent_executor(session_id, from_number)
        response = await agent_executor.ainvoke({
            "input": message
        })
        output = response.get("output", "Sorry, I couldn't process that request. Please try again.")
        
        await send_whatsapp_message(from_number, output)
     
        # Add agent message to history and publish via WebSocket
        agent_message = await SessionManager.append_message(session_id, "agent", output)
        await publish_message_created(session_id, agent_message)
        await publish_session_update(session_id, status, output)
        
        # return {
        #     "status": "completed",
        #     "session_id": session_id,
        #     "response_sent": True,
        #     "from_number": from_number
        # }
        
    except Exception as e:
        print(f"Agent error for {from_number}: {e}")
        error_output = "I'm experiencing some difficulties. Let me connect you with a human representative."

        try:
            await send_whatsapp_message(from_number, error_output)
            if session_id:
                await SessionManager.append_message(session_id, "agent", error_output)
        except:
            pass  # Don't fail if we can't send error message

        # HITL notify with WebSocket integration
        await notify_human_async(
            subject="Agent Failure",
            message=f"Agent failed for {from_number}: {str(e)}",
            context={
                "session_id": session_id,
                "from_number": from_number,
                "error": str(e),
                "last_message": message
            }
        )
        
        # Publish error status update
        if session_id:
            await publish_session_update(session_id, "need-human-support", f"Agent error: {str(e)[:50]}...")
            await publish_counts_update()
       
        return {
            "status": "error", 
            "session_id": session_id,
            "error": str(e),
            "from_number": from_number
        }

class WhatsAppService:
    def __init__(self):
        missing = [k for k,v in {
            "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
            "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
            "TWILIO_SANDBOX_NUMBER": TWILIO_WHATSAPP_NUMBER
        }.items() if not v]
        if missing:
            raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

    async def process_messages(self, messages: list[tuple[str, str]]) -> list[dict]:
        """Process multiple WhatsApp messages concurrently using asyncio.gather"""
        if not messages:
            return []
            
        # Create tasks for all messages
        tasks = [
            process_whatsapp_message(from_number, message) 
            for from_number, message in messages
        ]
        
        # Process all messages concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                from_number, message = messages[i]
                print(f"Exception processing message from {from_number}: {result}")
                processed_results.append({
                    "status": "exception",
                    "from_number": from_number,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def process_single_message(self, from_number: str, message: str) -> dict:
        """Process a single message (wrapper for backward compatibility)"""
        return await process_whatsapp_message(from_number, message)