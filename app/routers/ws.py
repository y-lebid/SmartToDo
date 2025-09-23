from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/notify")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text("Connected to notifications!")
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Echo: {data}")
