from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import re

class ConversationBase(BaseModel):
    id: Optional[int] = None
    first_person: int
    second_person: int
    
    
class ConversationCreate(ConversationBase):
    pass

class ConversationRead(ConversationBase):
    pass

class ConversationRequest(BaseModel):
    id: int

class ConversationOut(BaseModel):
    id: int
    first_user_id: Optional[int] = None
    second_user_id: Optional[int] = None
    created: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }