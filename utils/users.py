from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from config.db import get_db
from models import UserModel, LikeModel
from models.message_model import MessageModel
from .follows import verify_follow



def get_user_email(db:Session, email:str) -> UserModel:
    return db.query(UserModel).filter(UserModel.email == email).first()

def get_by_username(db:Session, username:str) -> UserModel:
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_id (id: int, db:Session) -> UserModel:
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise ValueError('User not found')
    
    return user

def user_like (user:UserModel, post: LikeModel):
    likes = user.likes
    for like in likes:
        if like['id'] == post.id:
            return True
    
    return False


def get_last_message(id:int, token:dict, db: Session = Depends(get_db)):
    try:
        current_user = token["id"]

        last_message = db.query(MessageModel).filter(MessageModel.conversation_id == id).order_by(MessageModel.created.desc()).first()
        unread_messages = (
            select(func.count())
            .select_from(MessageModel)
            .where(
                MessageModel.conversation_id == id,
                MessageModel.sender_id != current_user,
                MessageModel.status == False
            )
        )
        count_unread_message = db.execute(unread_messages).scalar_one()
        return {
            "last_message": last_message,
            "count_unread_messages": count_unread_message
        }
        
    except ValueError as e:
        print(e)
