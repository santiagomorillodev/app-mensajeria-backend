from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Header
from models import UserModel, ConversationModel, MessageModel
from schemas import UserConversation, ConversationOut, TokenRead
from sqlalchemy import and_, or_, select, func
from sqlalchemy.orm import Session
from config import get_db
from security import get_current_user, jwt
 

root = APIRouter(prefix='/api/v1/conversation', tags=['Conversation'])


def search_conversation(current_user: UserModel, user_2: UserModel, db: Session):
    return db.query(ConversationModel).filter(
        or_(
            and_(
                ConversationModel.first_user_id == current_user.id,
                ConversationModel.second_user_id == user_2.id
            ),
            and_(
                ConversationModel.first_user_id == user_2.id,
                ConversationModel.second_user_id == current_user.id
            )
        )
    ).first()

def get_last_message(
    id: int,
    token: dict,
    db: Session
):

    current_user = token["id"]


    last_message = (
        db.query(MessageModel)
        .filter(
            MessageModel.conversation_id == id
        )
        .order_by(
            MessageModel.created.desc()
        )
        .first()
    )


    unread_messages = (
        select(func.count())
        .select_from(MessageModel)
        .where(

            MessageModel.conversation_id == id,

            MessageModel.sender_id != current_user,

            MessageModel.status == False
        )
    )


    count_unread_message = (
        db.execute(unread_messages)
        .scalar_one()
    )


    return {

        "last_message":
            last_message,

        "count_unread_messages":
            count_unread_message
    }



@root.get('/all')
def get_all_conversation(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization header missing'
        )

    token = (
        authorization.split(" ")[1]
        if " " in authorization
        else authorization
    )

    current_user = jwt.decode_access_token(
        token=token
    )

    if not current_user or "id" not in current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired credentials'
        )

    user_id = current_user["id"]
    conversations = (
        db.query(ConversationModel)
        .filter(
            or_(
                ConversationModel.first_user_id == user_id,
                ConversationModel.second_user_id == user_id
            )).all())

    if not conversations:
        return []

    result = []

    for conv in conversations:

        if conv.first_user_id == user_id:
            other_user = conv.second_user
            recipient_id = conv.second_user_id
        else:
            other_user = conv.first_user
            recipient_id = conv.first_user_id

        last_message_info = get_last_message(conv.id, current_user, db)

        result.append({
            "conversation_id": conv.id,
            "recipient_id": recipient_id,
            "name": other_user.name if other_user else "",              
            "username": other_user.username if other_user else "",      
            "photo": getattr(other_user, 'avatar_url', getattr(other_user, 'photo_url', '')),
            "last_message": last_message_info.get("last_message", ""),
            "count_unread_messages": last_message_info.get("count_unread_messages", 0)
        })

    return result
        
@root.post('/create/{user}')
def create_conversation(
    user: int, 
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    current_user = get_current_user(authorization, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )

    target_user = db.query(UserModel).filter(UserModel.id == user).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='Usuario no encontrado'
        )

    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No puedes crear una conversación contigo mismo'
        )

    conversation = search_conversation(current_user, target_user, db)
    if conversation:
        return conversation

    new_conversation = ConversationModel(
        first_user_id=current_user.id,
        second_user_id=target_user.id
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return new_conversation

@root.get('/{second_user}')
def get_conversation(second_user:int, authorization: str = Header(None), db:Session = Depends(get_db)):
    try:

        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token=token)

        user = db.query(UserModel).filter(UserModel.id == second_user).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='The user not exist'
            )
        
        conversation = search_conversation(current_user, user, db)
        other_user = (conversation.second_user if conversation.first_user_id == current_user["id"] else conversation.first_user)
        last_message = get_last_message(conversation.id, current_user, db)

        result = {
            "conversation_id": conversation.id,
            "name": other_user.username,
            "photo": other_user.avatar_url,
            "last_message": last_message["last_message"],
            "count_unread_messages": last_message["count_unread_messages"]
        }
        
        return result
    

    except ValueError as error:
        print(error)
        





@root.get("/unread")
def unread_messages(token:TokenRead, db: Session = Depends(get_db)):
    current_user = jwt.decode_access_token(token=token.token)
    rows = db.execute(
        select(
            MessageModel.conversation_id,
            func.count().label("unread")
        )
        .where(
            MessageModel.sender_id != current_user["id"],
            MessageModel.status == False
        )
        .group_by(MessageModel.conversation_id)
    ).all()

    return { row.conversation_id: row.unread for row in rows }


@root.delete('/')
def delete_conversation(user:UserConversation, authorization:str = Header(None), db:Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token=token)
        conversation = search_conversation(current_user, user, db)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='The conversation not exist'
            )
        db.delete(conversation)
        db.commit()
        return 'Conversation delete'
    except ValueError as error:
        print(error)