import asyncio
import os
from dotenv import load_dotenv
import httpx
from backend.service.session_manager import SessionManager
from langchain.agents import AgentExecutor
from backend.agent.chat_agent import agent, tools, get_memory
from backend.service.hitl import notify_human


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
    print(f"Agent reply:{message}")
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
    try:
        session_id = await session_manager.get_or_create_session(from_number)
        
        # Get memory for this session
        memory = get_memory(session_id)

        # Build executor with memory
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=False,  # Turn off verbose in production
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=False
        )

        response = await agent_executor.ainvoke({
            "input": message
        })

        output = response.get("output", "Sorry, I couldn't process that request. Please try again.")
        
        # Send response back to user
        await send_whatsapp_message(from_number, output)
        
        return {
            "status": "completed",
            "session_id": session_id,
            "response_sent": True,
            "from_number": from_number
        }
        
    except Exception as e:
        print(f"Agent error for {from_number}: {e}")
        error_output = "Sorry, I encountered an error processing your request. Please try again."

        # HITL notify
        notify_human(
            subject="Agent Failure",
            message=f"Agent failed for {from_number}",
            context={"error": str(e), "last_message": message}
        )        
        return {
            "status": "error", 
            "session_id": session_id if 'session_id' in locals() else None,
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
        """
        Process multiple WhatsApp messages concurrently using asyncio.gather
        
        Args:
            messages: List of (from_number, message) tuples
            
        Returns:
            List of processing results
        """
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