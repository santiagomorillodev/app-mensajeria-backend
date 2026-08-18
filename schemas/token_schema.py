from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
import re
from datetime import datetime

class TokenBase(BaseModel):
    token: str

class TokenRead(TokenBase):
    pass