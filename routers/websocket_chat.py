from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from config.session import SessionLocal
from models import ConversationModel, MessageModel
from sockets import ConnectionManager

router = APIRouter(
    prefix="/api/v1/ws",
    tags=["WebSocket"],
)

manager = ConnectionManager()


print("🔥🔥🔥 SOCKET.PY CARGADO 🔥🔥🔥")
print("🔥🔥🔥 ROUTER WEBSOCKET CREADO 🔥🔥🔥")

class SendMessageSchema(BaseModel):
    type: str
    conversation_id: int
    content: str

class MarkReadSchema(BaseModel):
    type: str
    conversation_id: int


def fetch_user_conversations(user_id: int, db: Session) -> List[dict]:
    conversations = (
        db.query(ConversationModel)
        .options(
            joinedload(ConversationModel.first_user),
            joinedload(ConversationModel.second_user)
        )
        .filter(
            or_(
                ConversationModel.first_user_id == user_id,
                ConversationModel.second_user_id == user_id
            )
        )
        .all()
    )

    if not conversations:
        return []

    result = []
    for conv in conversations:
        is_first_user = conv.first_user_id == user_id
        other_user = conv.second_user if is_first_user else conv.first_user
        recipient_id = conv.second_user_id if is_first_user else conv.first_user_id

        last_message = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == conv.id)
            .order_by(MessageModel.created.desc())
            .first()
        )

        unread_count = (
            db.query(func.count(MessageModel.message_id))
            .filter(
                MessageModel.conversation_id == conv.id,
                MessageModel.sender_id != user_id,
                MessageModel.status == False
            )
            .scalar()
        )

        last_message_data = None
        if last_message:
            last_message_data = {
                "message_id": last_message.message_id,
                "sender_id": last_message.sender_id,
                "conversation_id": last_message.conversation_id,
                "content": last_message.content,
                "image_url": getattr(last_message, "image_url", None),
                "public_id": getattr(last_message, "public_id", None),
                "created": last_message.created.isoformat() if last_message.created else None,
                "status": last_message.status
            }

        result.append({
            "conversation_id": conv.id,
            "recipient_id": recipient_id,
            "name": getattr(other_user, "name", "") if other_user else "",
            "username": getattr(other_user, "username", "") if other_user else "",
            "photo": getattr(other_user, "avatar_url", "") if other_user else "",
            "last_message": last_message_data,
            "count_unread_messages": unread_count or 0
        })

    return result


def get_conversation_for_users(conversation_id: int, user_id: int, db: Session) -> Optional[ConversationModel]:
    return (
        db.query(ConversationModel)
        .filter(
            ConversationModel.id == conversation_id,
            or_(
                ConversationModel.first_user_id == user_id,
                ConversationModel.second_user_id == user_id
            )
        )
        .first()
    )


@router.websocket("/test")
async def websocket_test(websocket: WebSocket):

    print("🔥🔥🔥 PETICIÓN WEBSOCKET TEST RECIBIDA 🔥🔥🔥")

    await websocket.accept()

    print("🔥🔥🔥 WEBSOCKET TEST ACEPTADO 🔥🔥🔥")

    await websocket.send_json({
        "type": "test",
        "message": "WebSocket funcionando correctamente en Render"
    })

    try:
        while True:
            data = await websocket.receive_json()

            print("📩 TEST RECIBIDO:", data)

            await websocket.send_json({
                "type": "echo",
                "data": data
            })

    except WebSocketDisconnect:

        print("🔴 TEST WEBSOCKET DESCONECTADO")

@router.websocket("/user/{user_id}")
async def user_socket(websocket: WebSocket, user_id: int):
    print("🔥🔥🔥 WEBSOCKET ENDPOINT ALCANZADO 🔥🔥🔥")
    print(f"🔥 USER ID: {user_id}")
    await manager.connect(user_id, websocket)

    with SessionLocal() as db:
        conversations_data = fetch_user_conversations(user_id, db)
        await websocket.send_json({
            "type": "conversation_sync",
            "conversations": conversations_data
        })

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            with SessionLocal() as db:
                try:
                    if event_type == "send_message":
                        payload = SendMessageSchema(**data)
                        content_clean = payload.content.strip()

                        if not content_clean:
                            await websocket.send_json({"type": "error", "message": "El mensaje está vacío"})
                            continue

                        conversation = get_conversation_for_users(payload.conversation_id, user_id, db)
                        if not conversation:
                            await websocket.send_json({"type": "error", "message": "No perteneces a esta conversación"})
                            continue

                        recipient_id = (
                            conversation.second_user_id if conversation.first_user_id == user_id 
                            else conversation.first_user_id
                        )

                        new_message = MessageModel(
                            sender_id=user_id,
                            conversation_id=payload.conversation_id,
                            content=content_clean,
                            status=False
                        )
                        db.add(new_message)
                        db.commit()
                        db.refresh(new_message)

                        message_data = {
                            "message_id": new_message.message_id,
                            "sender_id": new_message.sender_id,
                            "conversation_id": new_message.conversation_id,
                            "content": new_message.content,
                            "image_url": getattr(new_message, "image_url", None),
                            "public_id": getattr(new_message, "public_id", None),
                            "created": new_message.created.isoformat() if new_message.created else None,
                            "status": new_message.status
                        }

                        await manager.send_personal_message({"type": "new_message", "message": message_data, "is_sender": True}, user_id)
                        await manager.send_personal_message({"type": "new_message", "message": message_data, "is_sender": False}, recipient_id)

                        sender_convs = fetch_user_conversations(user_id, db)
                        recipient_convs = fetch_user_conversations(recipient_id, db)

                        await manager.send_personal_message({"type": "conversation_update", "conversations": sender_convs}, user_id)
                        await manager.send_personal_message({"type": "conversation_update", "conversations": recipient_convs}, recipient_id)

                    elif event_type == "mark_messages_read":
                        payload = MarkReadSchema(**data)
                        
                        conversation = get_conversation_for_users(payload.conversation_id, user_id, db)
                        if not conversation:
                            await websocket.send_json({"type": "error", "message": "No perteneces a esta conversación"})
                            continue

                        db.query(MessageModel).filter(
                            MessageModel.conversation_id == payload.conversation_id,
                            MessageModel.sender_id != user_id,
                            MessageModel.status == False
                        ).update({MessageModel.status: True}, synchronize_session=False)
                        db.commit()

                        conversations_data = fetch_user_conversations(user_id, db)
                        await websocket.send_json({
                            "type": "conversation_update",
                            "conversations": conversations_data
                        })

                    else:
                        await websocket.send_json({"type": "error", "message": f"Unknown event type: {event_type}"})

                except Exception as inner_error:
                    db.rollback()
                    await websocket.send_json({"type": "error", "message": f"Error procesando evento: {str(inner_error)}"})

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)