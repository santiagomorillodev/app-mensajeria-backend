from models import MessageModel

async def save_message_to_db(
    sender_id: int,
    conversation_id: int,
    content: str | None,
    image_url: str | None,
    public_id: str | None,
    database,
):
    message = MessageModel(
        sender_id=sender_id,
        conversation_id=conversation_id,
        content=content,
        image_url=image_url,
        public_id=public_id,
    )

    database.add(message)
    database.commit()
    database.refresh(message)
    return message
