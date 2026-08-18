from pydantic import BaseModel
from datetime import datetime

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageBase(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    conversation_id: int

class MessageCreate(MessageBase):
    pass

class MessageResponse(BaseModel):
    message_id: int
    sender_id: int
    conversation_id: int
    content: Optional[str] = None
    image_url: Optional[str] = None
    status: bool
    created: datetime

    class Config:
        orm_mode = True
        

class MessageRead(MessageBase):
    pass
    
class MessageRequest(BaseModel):
    id: int
    
class MessageDelete(BaseModel):
    password: str


