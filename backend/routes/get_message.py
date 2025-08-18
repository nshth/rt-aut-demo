# from fastapi import APIRouter, HTTPException
# from backend.db.schema import ChatRequest
# from backend.agent.chat_agent import llm,tools, executor
# import logging

# router = APIRouter()
# @router.post("/chat")
# async def chat_endpoint(request: ChatRequest):

#     try:
#         if not request.message:
#             return {"sessionId": request.sessionId, "reply": "I didn't receive a message. Could you please try again?"}
        
#         response = executor.invoke({"input": request.message})
        
#         if not response or not response.get("output"):
#             return {"sessionId": request.sessionId, "reply": "I'm having trouble processing your request right now. Please try again in a moment."}
        
#         return {"sessionId": request.sessionId, "reply": response["output"]}
    
#     except Exception as e: 
#         logging.error(f"Error in chat endpoint: {str(e)}")
#         return {"sessionId": request.sessionId, "reply": f"I encountered an error while processing your request: {str(e)}"}


