from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/test")
async def receive_json(request: Request):
    body = await request.json()
    print("Received body:", body)
    return {"status": "received", "body": body}

