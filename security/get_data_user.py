from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException,status, Cookie
from sqlalchemy.orm import Session
from config import get_db
from utils.users import get_user_by_id
from .jwt import decode_access_token
from utils import get_by_username
from models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def get_user(authorization:str)-> dict:
    token = authorization.split(" ")[1] if authorization else None
    current_user = decode_access_token(token)
    return current_user



def get_current_user(authorization: str, db: Session = Depends(get_db)) -> UserModel:
    token = authorization.split(" ")[1] if authorization else None
    user = decode_access_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token not provided'
        )

    

    user_id = user["id"]
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token payload'
        )

    user = get_user_by_id(id=user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found'
        )

    return user