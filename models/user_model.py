from config import Base
from sqlalchemy import Integer, DateTime, String, func, CheckConstraint, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
class UserModel(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=True, default='https://res.cloudinary.com/dyteo3qdh/image/upload/v1760837715/usuario_yrdfvf.png')
    banner_url: Mapped[str] = mapped_column(String(512), nullable=True, default='https://res.cloudinary.com/dyteo3qdh/image/upload/v1763515954/descarga_6_aqzzby.jpg')
    avatar_public_id: Mapped[str] = mapped_column(String(255), nullable=True)
    banner_public_id: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint('age >= 18', name='check_age'),
        CheckConstraint('length(name) >= 3'),
        CheckConstraint('length(password) >= 8')
    )

    conversation_first_user = relationship(
        'ConversationModel',
        back_populates='first_user',
        foreign_keys='ConversationModel.first_user_id',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    conversation_second_user = relationship(
        'ConversationModel',
        back_populates='second_user',
        foreign_keys='ConversationModel.second_user_id',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    messages = relationship(
        'MessageModel',
        back_populates='sender',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    following = relationship(
        'FollowerModel',
        foreign_keys='FollowerModel.follower_id',
        back_populates='follower',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    followers = relationship(
        'FollowerModel',
        foreign_keys='FollowerModel.followed_id',
        back_populates='followed',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    recent_Search = relationship(
        'RecentModel',
        foreign_keys='RecentModel.user_id',
        back_populates='user',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    other = relationship(
        'RecentModel',
        foreign_keys='RecentModel.other_user',
        back_populates='second',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    posts = relationship(
        'PostModel',
        back_populates='user',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    likes = relationship(
        "LikeModel",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    notifications = relationship(
        "NotificationModel",
        foreign_keys="NotificationModel.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    notifications_from_others = relationship(
        "NotificationModel",
        foreign_keys="NotificationModel.other_user_id",
        back_populates="other_user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
