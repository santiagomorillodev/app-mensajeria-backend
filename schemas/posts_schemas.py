from pydantic import BaseModel, EmailStr, validator, ConfigDict
from typing import Optional
import re
from datetime import datetime

class PostBase(BaseModel):
    name: str
    age: int 
    post:str
    
    
class PostCreate(PostBase):
    email: EmailStr
    password: str
    avatar_url:Optional[str] = None
