from config import Base
from sqlalchemy import Column, Text, Integer, ForeignKey, func, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class MessageModel(Base):
    __tablename__ = 'messages'
    
    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sender = relationship('UserModel', back_populates='messages')
    conversation = relationship('ConversationModel', back_populates='messages')