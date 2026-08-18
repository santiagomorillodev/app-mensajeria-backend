from config import Base
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class ConversationModel(Base):
    __tablename__ = 'conversations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    second_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    first_user = relationship('UserModel', foreign_keys=[first_user_id])
    second_user = relationship('UserModel', foreign_keys=[second_user_id])
    messages = relationship('MessageModel', back_populates='conversation', cascade="all, delete-orphan", passive_deletes=True)
