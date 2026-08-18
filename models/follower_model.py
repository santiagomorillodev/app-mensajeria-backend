from config import Base
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class FollowerModel(Base):
    __tablename__ = 'followers'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    followed_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('follower_id', 'followed_id', name='uix_user_follow'),
    )

    follower = relationship('UserModel', foreign_keys=[follower_id], back_populates='following')
    followed = relationship('UserModel', foreign_keys=[followed_id], back_populates='followers')
