import time
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from backend.service.whatsapp_service import WhatsAppService

router = APIRouter()
wa_service = WhatsAppService()

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()   
    from_number = form.get("From", "").replace("whatsapp:", "")
    message = form.get("Body", "")

    if not from_number or not message:
        return {"status": "ignored"}

    print(f"[{time.strftime('%H:%M:%S')}] Queued message from {from_number}")
    
    # Add to background tasks
    background_tasks.add_task(
        wa_service.process_single_message, 
        from_number, 
        message
    )
    
    return {"status": "received"} 