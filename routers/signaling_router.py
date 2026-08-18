from fastapi import APIRouter, WebSocket
from typing import Dict

router = APIRouter()

active_connections: Dict[int, WebSocket] = {}

@router.websocket("/ws/signaling/{user_id}")
async def signaling_socket(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket
    print("User connected:", user_id)

    try:
        while True:
            data = await websocket.receive_json()

            target = data.get("target")
            if not target:
                # Si no hay target especificado, no reenviar
                continue

            if target == user_id:
                # Ignorar mensajes a sí mismo
                continue

            if target in active_connections:
                await active_connections[target].send_json(data)
            else:
                print(f"Target {target} not connected")

    except Exception as e:
        print("ERROR:", e)

    finally:
        # Limpiar conexión
        if user_id in active_connections:
            del active_connections[user_id]
        print("User disconnected:", user_id)
