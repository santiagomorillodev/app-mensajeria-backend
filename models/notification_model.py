from config import Base
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, Text,Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class NotificationModel(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    other_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship('UserModel', foreign_keys=[user_id], back_populates='notifications')
    other_user = relationship('UserModel', foreign_keys=[other_user_id], back_populates='notifications_from_others')
