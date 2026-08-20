from pydantic import BaseModel
from typing import Optional


class PostCreate(BaseModel):
    content: Optional[str] = None
    image_base64: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    content: Optional[str] = None
    url: Optional[str] = None
    public_id: Optional[str] = None
    created: Optional[str] = None