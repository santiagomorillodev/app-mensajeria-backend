from fastapi import APIRouter, File, Form, HTTPException, Header, UploadFile, status, Depends
from models import MessageModel, ConversationModel
from cloudinary import uploader
from schemas import MessageCreate, MessageResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from config import get_db
from security import jwt


root = APIRouter(prefix="/api/v1/messages", tags=['Messages'])
        
        
@root.post('/')
def create_message(message: MessageCreate, authorization:str = Header(None), db: Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token)
        print(current_user)
        user_in_conversation = db.query(ConversationModel).filter(((ConversationModel.first_user_id == current_user["id"]) | (ConversationModel.second_user_id == current_user["id"]))).first()

        if not user_in_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't belong in that conversation."
            )
        conversation = db.query(ConversationModel).filter(ConversationModel.id == message.conversation_id).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='The conversations not exist'
            )
            
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid credentials'
            )
        
        new_message = MessageModel(
            sender_id = current_user["id"],
            content = message.content,
            conversation_id=message.conversation_id
        )
        
        db.add(new_message)
        db.commit()
        return message
    except ValueError as error:
        print(error)
        

@root.get("/chat-{id}", response_model=list[MessageResponse])
def get_messages(
    id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    try:

        token = (
            authorization.split(" ")[1]
            if authorization
            else None
        )

        current_user = jwt.decode_access_token(
            token
        )


        if not current_user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )


        conversation_db = (
            db.query(ConversationModel)
            .filter(
                ConversationModel.id == id
            )
            .first()
        )


        if not conversation_db:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The conversation does not exist"
            )

        if (
            conversation_db.first_user_id
            != current_user["id"]
            and
            conversation_db.second_user_id
            != current_user["id"]
        ):

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't belong to this conversation."
            )


        messages = (
            db.query(MessageModel)
            .filter(
                MessageModel.conversation_id == id
            )
            .order_by(
                MessageModel.created.asc()
            )
            .all()
        )


        return messages


    except ValueError as error:

        print(error)

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
@root.delete('/delete-{message}')
def delete_message(message: int, authorization:str = Header(None), db:Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token)
        message_db = db.query(MessageModel).filter(((MessageModel.message_id == message) & (MessageModel.sender_id == current_user["id"]))).first()
        if not message_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Message not found'
            )
        
        db.delete(message_db)
        db.commit()
        return 'Message Deleted'
    except ValueError as error:
        print(error)
        
@root.post('/message/change-status/{conversation_id}')
def change_status(conversation_id: int, authorization:str = Header(None), db: Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token)
        conversation_db = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conversation_db:
            return
        db.query(MessageModel).filter(and_(MessageModel.sender_id != current_user["id"], MessageModel.conversation_id == conversation_id)).update({MessageModel.status : True})
        db.commit()
        return 'User status changed'
        
        
    except ValueError as e:
        raise HTTPException (status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))