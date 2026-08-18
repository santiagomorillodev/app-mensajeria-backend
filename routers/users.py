from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Header, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func, or_, select
from schemas import UserCreate,UserRead,UserDeleteRequest,UserUpdate,UserLikes, UserPassword, UserEmail, UserReadMe, UserSearchRead
from models import UserModel, FollowerModel, LikeModel, RecentModel,PostModel, NotificationModel, ConversationModel
from security.get_data_user import get_user
from utils import get_user_email, get_by_username, verify_follow, get_user_by_id
from config import get_db
from security import hash_password, verify_password, create_access_token, get_current_user
from datetime import datetime, timedelta, timezone
from cloudinary import uploader

root = APIRouter(prefix="/api/v1", tags=["Users"])


@root.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    email = get_user_email(db, user.email)
    user_username = get_by_username(db, user.username)
    if email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "The email is already in use"},
        )

    if user_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "The username is already in use"},
        )

    new_user = UserModel(
        name=user.name,
        age=user.age,
        email=user.email,
        username=user.username,
        password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User Created"}


@root.post('/login')
def login(data:OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
    print(data.username)
    
    try:
        user_db = db.query(UserModel).filter(UserModel.username == data.username).first()
        print(user_db)
        if not user_db or not verify_password(data.password, user_db.password):
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='invalid credentials'
            )
            
        token = create_access_token({'sub': user_db.username, 'id': user_db.id})

        db.query(UserModel).filter(UserModel.id == user_db.id).update({UserModel.status: True})
        db.commit()
        db.refresh(user_db)
        return token
    
    except ValueError as error:
        print(error)


@root.get("/me", response_model=UserReadMe)
def current_user(authorization: str = Header(None), db:Session = Depends(get_db)):
    current_user = get_user(authorization)

    followers_subquery = (
        select(func.count(FollowerModel.id))
        .where(FollowerModel.followed_id == current_user["id"])
        .scalar_subquery()
    )

    following_subquery = (
        select(func.count(FollowerModel.id))
        .where(FollowerModel.follower_id == current_user["id"])
        .scalar_subquery()
    )

    stmt = (
        select(
            UserModel,
            followers_subquery.label("followers_count"),
            following_subquery.label("following_count")
        )
        .where(UserModel.id == current_user["id"])
    )

    result = db.execute(stmt).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    user_obj, followers_count, following_count = result

    user_data = {
        **user_obj.__dict__,
        "followers_count": followers_count,
        "following_count": following_count,
    }

    return UserReadMe.model_validate(user_data)

@root.get("/user/{id}")
def get_user_data(
    id: int, 
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    current_user = None
    if authorization:
        try:
            current_user = get_current_user(authorization=authorization, db=db)
            current_user_id = current_user.id
        except Exception:
            current_user_id = None

    user = db.query(UserModel).filter(UserModel.id == id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )

    is_liked_subquery = (
        select(func.count(LikeModel.id) > 0)
        .where(
            and_(
                LikeModel.post_id == PostModel.id,
                LikeModel.user_id == current_user_id
            )
        )
        .correlate(PostModel)
        .scalar_subquery()
    )

    posts_query = (
        db.query(
            PostModel,
            func.count(LikeModel.id).label("likes_count"),
            is_liked_subquery.label("is_liked")
        )
        .outerjoin(LikeModel, LikeModel.post_id == PostModel.id)
        .filter(PostModel.id_user == id)
        .group_by(PostModel.id)
        .order_by(desc(PostModel.id))
        .all()
    )

    is_following = verify_follow(current_user=current_user, second_user=id, db=db)

    formatted_posts = [
        {
            "id": post.id,
            "content": post.content,
            "image_url": post.url,
            "created_at": post.created.isoformat() if hasattr(post, "created") and post.created else None,
            "likes_count": likes_count,
            "is_liked": bool(is_liked) if current_user_id else False,
        }
        for post, likes_count, is_liked in posts_query
    ]

    total_given_likes = len(user.likes) if user.likes else 0

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "age": user.age,
        "photo": user.avatar_url,
        "banner": user.banner_url,
        "description": user.description,
        "is_following": is_following,
        "posts": formatted_posts,
        "likes_given": total_given_likes
    }


@root.get("/following")
def get_followed(authorization: str = Header(None), db: Session = Depends(get_db)):
    current_user = get_current_user(authorization=authorization, db=db)
    
    if not current_user or not current_user.following:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "You don't follow anyone"})

    conversation_subquery = (
        select(ConversationModel.id)
        .where(
            or_(
                and_(
                    ConversationModel.first_user_id == current_user.id,
                    ConversationModel.second_user_id == UserModel.id
                ),
                and_(
                    ConversationModel.first_user_id == UserModel.id,
                    ConversationModel.second_user_id == current_user.id
                )
            )
        )
        .correlate(UserModel)  
        .scalar_subquery()
    )

    stmt = (
        select(
            UserModel.id,
            UserModel.username,
            UserModel.name,
            UserModel.avatar_url,
            conversation_subquery.label("conversation_id")
        )
        .join(FollowerModel, FollowerModel.followed_id == UserModel.id)
        .where(FollowerModel.follower_id == current_user.id)
    )

    results = db.execute(stmt).all()

    return [
        {
            "id": row.id,
            "username": row.username,
            "full_name": row.name,
            "avatar_url": row.avatar_url,
            "conversation_id": row.conversation_id  
        }
        for row in results
    ]



@root.post("/like")
async def toggle_likes(post: UserLikes, authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_user(authorization)
    post_db = db.query(PostModel).filter(PostModel.id == post.post_id).first()
    if not post_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    exist_like = db.query(LikeModel).filter(and_(LikeModel.user_id == user["id"], LikeModel.post_id == post.post_id)).first()

    if exist_like:
        db.delete(exist_like)
        db.commit()
    else:
        new_like = LikeModel(user_id=user["id"], post_id=post.post_id)
        db.add(new_like)
        db.commit()
    
    following_ids = db.query(FollowerModel.followed_id).filter(FollowerModel.follower_id == user["id"]).all()
    for id in following_ids:
        followed_id = id[0]
        new_notification = NotificationModel(
            user_id = followed_id,
            other_user_id = user["id"],
            content = 'Le ha dado like a tu post!'
        )
        if new_notification:
            db.add(new_notification)
            db.commit()
    return status.HTTP_200_OK

@root.get("/likes")
async def get_likes(authorization: str = Header(None), db:Session = Depends(get_db)):
    current_user = get_user(authorization=authorization)
    user = get_user_by_id(current_user["id"], db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user.likes

@root.patch("/update/password")
async def update_password( new_password: str = Form(None), password: str = Form(None), authorization: str = Header(None), db: Session = Depends(get_db)):

    try:
        current_user = get_current_user(authorization, db)
        
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
        if not verify_password(password, current_user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    
        hashed_password = hash_password(new_password)
        db.query(UserModel).filter(UserModel.id == current_user.id).update({UserModel.password: hashed_password})
    
        db.commit()
        db.refresh(current_user)
    
        return {"message": "User updated successfully"}
    except ValueError as exc:
        return None


@root.patch("/update/username")
async def update_username( username: str = Form(None),authorization: str = Header(None), db: Session = Depends(get_db)):

    current_user = get_current_user(authorization, db)

    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


    if username:
        current_user.username = username

    db.commit()
    db.refresh(current_user)

    return {"message": "User updated successfully"}


@root.patch("/update/email")
async def update_email( email: str = Form(None), password: str = Form(None), authorization: str = Header(None), db: Session = Depends(get_db)):

    current_user = get_current_user(authorization, db)

    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if current_user.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')

    if email:
        current_user.email = email

    db.commit()
    db.refresh(current_user)

    return {"message": "User updated successfully"}


@root.get("/search/users", response_model=List[UserSearchRead])
def search_users(
    q: str = Query("", min_length=1), 
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    current_user = get_current_user(authorization, db)

    query_str = f"%{q.strip().lower()}%"

    users = db.query(UserModel).filter(
        and_(
            UserModel.id != current_user.id,
            or_(
                UserModel.username.ilike(query_str),
                UserModel.name.ilike(query_str)
            )
        )
    ).limit(20).all()

    if not users:
        return []

    user_ids = [u.id for u in users]

    following_ids = set(
        f.followed_id for f in db.query(FollowerModel.followed_id).filter(
            and_(
                FollowerModel.follower_id == current_user.id,
                FollowerModel.followed_id.in_(user_ids)
            )
        ).all()
    )

    results = []
    for user in users:
        user_data = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "photo": user.avatar_url,
            "following": user.id in following_ids
        }
        results.append(UserSearchRead.model_validate(user_data))

    return results


@root.post("/search/recent/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_recent_search(
    target_user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(authorization, db)

    if current_user.id == target_user_id:
        return

    recent = db.query(RecentModel).filter(
        and_(
            RecentModel.user_id == current_user.id,
            RecentModel.other_user == target_user_id
        )
    ).first()

    if not recent:
        new_search = RecentModel(user_id=current_user.id, other_user=target_user_id)
        db.add(new_search)
    else:
        recent.created = datetime.now(timezone.utc)

    db.commit()
    return


@root.post("/follow/{followed}")
async def toggle_follow(
    followed: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(authorization=authorization, db=db)
    if followed == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )

    exist_follow = (
        db.query(FollowerModel)
        .filter(
            and_(
                FollowerModel.follower_id == current_user.id,
                FollowerModel.followed_id == followed
            )
        )
        .first()
    )

    if exist_follow:
        db.delete(exist_follow)
        db.commit()
        following = False
    else:
        new_follow = FollowerModel(
            follower_id=current_user.id,
            followed_id=followed
        )
        db.add(new_follow)

        new_notification = NotificationModel(
            user_id=followed,
            other_user_id=current_user.id,
            content="¡Te ha comenzado a seguir!"
        )
        db.add(new_notification)
        db.commit()
        following = True

    follows_count = (
        db.query(FollowerModel)
        .filter(FollowerModel.followed_id == followed)
        .count()
    )

    return {
        "following": following,   
        "follows": follows_count  
    }

