from config import Base
from sqlalchemy import Column, Text, Integer, ForeignKey, func, DateTime, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class PostModel(Base):
    __tablename__ = 'post'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    public_id: Mapped[Text] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship('UserModel', back_populates='posts')
    likes = relationship("LikeModel", back_populates="post", cascade="all, delete-orphan", passive_deletes=True)
