from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from config import get_db
from models import (
    ConversationModel,
    MessageModel
)
from sockets import ConnectionManager
from utils import get_last_message


router = APIRouter(
    prefix="/api/v1/ws",
    tags=["WebSocket"],
)


manager = ConnectionManager()


# ============================================================
# OBTENER CONVERSACIONES DEL USUARIO
# ============================================================

def fetch_user_conversations(
    user_id: int,
    db: Session
) -> List[dict]:

    conversations = (
        db.query(ConversationModel)
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

    current_user_dict = {
        "id": user_id
    }


    for conv in conversations:

        if conv.first_user_id == user_id:

            other_user = conv.second_user
            recipient_id = conv.second_user_id

        else:

            other_user = conv.first_user
            recipient_id = conv.first_user_id


        last_message_info = (
            get_last_message(
                conv.id,
                current_user_dict,
                db
            )
            or {}
        )


        last_message = last_message_info.get(
            "last_message"
        )


        # Convertimos el objeto SQLAlchemy
        # a un JSON que React Native pueda recibir.
        if last_message:

            last_message_data = {
                "message_id": last_message.message_id,
                "sender_id": last_message.sender_id,
                "conversation_id": last_message.conversation_id,
                "content": last_message.content,
                "image_url": last_message.image_url,
                "public_id": last_message.public_id,
                "created": (
                    last_message.created.isoformat()
                    if last_message.created
                    else None
                ),
                "status": last_message.status
            }

        else:

            last_message_data = None


        result.append({

            "conversation_id": conv.id,

            "recipient_id": recipient_id,

            "name": (
                other_user.name
                if other_user
                else ""
            ),

            "username": (
                other_user.username
                if other_user
                else ""
            ),

            "photo": (
                getattr(
                    other_user,
                    "avatar_url",
                    ""
                )
                if other_user
                else ""
            ),

            "last_message": last_message_data,

            "count_unread_messages":
                last_message_info.get(
                    "count_unread_messages",
                    0
                )
        })


    return result


# ============================================================
# ENCONTRAR CONVERSACIÓN
# ============================================================

def get_conversation_for_users(
    conversation_id: int,
    user_id: int,
    db: Session
):

    conversation = (
        db.query(ConversationModel)
        .filter(
            ConversationModel.id == conversation_id
        )
        .first()
    )


    if not conversation:
        return None


    # El usuario debe pertenecer
    # específicamente a ESTA conversación.
    if (
        conversation.first_user_id != user_id
        and
        conversation.second_user_id != user_id
    ):

        return None


    return conversation


# ============================================================
# WEBSOCKET
# ============================================================

@router.websocket("/user/{user_id}")
async def user_socket(
    websocket: WebSocket,
    user_id: int,
    db: Session = Depends(get_db)
):

    await manager.connect(
        user_id,
        websocket
    )


    try:

        # ====================================================
        # SINCRONIZACIÓN INICIAL
        # ====================================================

        conversations_data = fetch_user_conversations(
            user_id,
            db
        )


        await websocket.send_json({

            "type": "conversation_sync",

            "conversations":
                conversations_data
        })


        # ====================================================
        # ESCUCHAR EVENTOS
        # ====================================================

        while True:

            data = await websocket.receive_json()

            print(
                f"📩 Evento WS recibido "
                f"de usuario {user_id}:",
                data
            )


            event_type = data.get("type")


            # =================================================
            # ENVIAR MENSAJE
            # =================================================

            if event_type == "send_message":

                conversation_id = data.get(
                    "conversation_id"
                )

                content = data.get(
                    "content",
                    ""
                ).strip()


                if not conversation_id:

                    await websocket.send_json({
                        "type": "error",
                        "message":
                            "conversation_id es requerido"
                    })

                    continue


                if not content:

                    await websocket.send_json({
                        "type": "error",
                        "message":
                            "El mensaje está vacío"
                    })

                    continue


                # ---------------------------------------------
                # BUSCAR CONVERSACIÓN
                # ---------------------------------------------

                conversation = (
                    get_conversation_for_users(
                        conversation_id,
                        user_id,
                        db
                    )
                )


                if not conversation:

                    await websocket.send_json({
                        "type": "error",
                        "message":
                            "No perteneces a esta conversación"
                    })

                    continue


                # ---------------------------------------------
                # IDENTIFICAR RECEPTOR
                # ---------------------------------------------

                if (
                    conversation.first_user_id
                    == user_id
                ):

                    recipient_id = (
                        conversation.second_user_id
                    )

                else:

                    recipient_id = (
                        conversation.first_user_id
                    )


                # ---------------------------------------------
                # CREAR MENSAJE
                # ---------------------------------------------

                new_message = MessageModel(

                    sender_id=user_id,

                    conversation_id=conversation_id,

                    content=content,

                    status=False
                )


                db.add(new_message)

                db.commit()

                db.refresh(new_message)


                # ---------------------------------------------
                # CREAR PAYLOAD
                # ---------------------------------------------

                message_data = {

                    "message_id":
                        new_message.message_id,

                    "sender_id":
                        new_message.sender_id,

                    "conversation_id":
                        new_message.conversation_id,

                    "content":
                        new_message.content,

                    "image_url":
                        new_message.image_url,

                    "public_id":
                        new_message.public_id,

                    "created":
                        (
                            new_message.created.isoformat()
                            if new_message.created
                            else None
                        ),

                    "status":
                        new_message.status
                }


                # ---------------------------------------------
                # ENVIAR AL EMISOR
                # ---------------------------------------------

                await manager.send_personal_message(

                    {
                        "type": "new_message",

                        "message": message_data,

                        "is_sender": True
                    },

                    user_id
                )


                # ---------------------------------------------
                # ENVIAR AL RECEPTOR
                # ---------------------------------------------

                await manager.send_personal_message(

                    {
                        "type": "new_message",

                        "message": message_data,

                        "is_sender": False
                    },

                    recipient_id
                )


                # ---------------------------------------------
                # ACTUALIZAR CONVERSACIONES
                # ---------------------------------------------

                sender_conversations = (
                    fetch_user_conversations(
                        user_id,
                        db
                    )
                )


                await manager.send_personal_message(

                    {
                        "type":
                            "conversation_update",

                        "conversations":
                            sender_conversations
                    },

                    user_id
                )


                recipient_conversations = (
                    fetch_user_conversations(
                        recipient_id,
                        db
                    )
                )


                await manager.send_personal_message(

                    {
                        "type":
                            "conversation_update",

                        "conversations":
                            recipient_conversations
                    },

                    recipient_id
                )


            # =================================================
            # MARCAR MENSAJES COMO LEÍDOS
            # =================================================

            elif event_type == "mark_messages_read":

                conversation_id = data.get(
                    "conversation_id"
                )


                if not conversation_id:

                    await websocket.send_json({
                        "type": "error",
                        "message":
                            "conversation_id es requerido"
                    })

                    continue


                # ---------------------------------------------
                # VERIFICAR CONVERSACIÓN
                # ---------------------------------------------

                conversation = (
                    get_conversation_for_users(
                        conversation_id,
                        user_id,
                        db
                    )
                )


                if not conversation:

                    await websocket.send_json({
                        "type": "error",
                        "message":
                            "No perteneces a esta conversación"
                    })

                    continue


                # ---------------------------------------------
                # MARCAR COMO LEÍDOS
                # ---------------------------------------------

                (
                    db.query(MessageModel)
                    .filter(
                        MessageModel.conversation_id
                        == conversation_id,

                        MessageModel.sender_id
                        != user_id,

                        MessageModel.status
                        == False
                    )
                    .update(
                        {
                            MessageModel.status: True
                        },

                        synchronize_session=False
                    )
                )


                db.commit()


                # ---------------------------------------------
                # ACTUALIZAR LISTA DEL USUARIO
                # ---------------------------------------------

                conversations_data = (
                    fetch_user_conversations(
                        user_id,
                        db
                    )
                )


                await websocket.send_json({

                    "type":
                        "conversation_update",

                    "conversations":
                        conversations_data
                })


            # =================================================
            # EVENTO DESCONOCIDO
            # =================================================

            else:

                print(
                    f"⚠️ Evento desconocido: "
                    f"{event_type}"
                )


                await websocket.send_json({

                    "type": "error",

                    "message":
                        f"Unknown event type: "
                        f"{event_type}"
                })


    except WebSocketDisconnect:

        manager.disconnect(
            user_id,
            websocket
        )


    except Exception as error:

        print(
            "❌ Error en WebSocket:",
            str(error)
        )

        manager.disconnect(
            user_id,
            websocket
        )