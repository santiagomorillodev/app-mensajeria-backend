from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException,status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from models import PostModel, UserModel, FollowerModel, NotificationModel, LikeModel
from config import get_db
from security import get_current_user, jwt
from cloudinary import uploader, api
from typing import Optional

root = APIRouter(prefix='/api/v1/post', tags=['Post'])

@root.post('/create')
async def create_post(
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    authorization:str = Header(),
    db: Session = Depends(get_db)
):
    if content == None and file == None: return
    try:
        token = authorization.split(" ")[1] if authorization else None
        current_user = jwt.decode_access_token(token)
        image_url = None
        public_id = None

        if file and file.filename:
            try:
                result = None
                if file.size != 0:
                    result = uploader.upload(
                        file.file,
                        resource_type="auto"
                    )
                    image_url = result.get('secure_url')
                    public_id = result.get('public_id')
                                    
            except Exception as upload_error:
                print(f"❌ Error subiendo imagen a Cloudinary: {upload_error}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error subiendo imagen: {str(upload_error)}"
                )

        post = PostModel(
            id_user=current_user["id"],
            content=content,
            url=image_url,      
            public_id=public_id 
        )
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        try:
            following_ids = db.query(FollowerModel.followed_id).filter(
                FollowerModel.follower_id == current_user["id"]
            ).all()
            
            for id_tuple in following_ids:
                followed_id = id_tuple[0]
                new_notification = NotificationModel(
                    user_id=followed_id,
                    other_user_id=current_user["id"],
                    content='ha subido un nuevo post!'
                )
                db.add(new_notification)
            
            db.commit()
            
        except Exception as notification_error:
            print(f"⚠️ Error creando notificaciones: {notification_error}")
            db.rollback()  

        return {
            "id": post.id,
            "content": post.content,
            "url": post.url,
            "public_id": post.public_id,
            "created": post.created
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"⚠️ Error crítico creando post: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando post: {str(e)}")

@root.get('/{id}')
def get_posts_current_user(id: int, db: Session = Depends(get_db)):
    try:
        posts = (
            db.query(PostModel)
            .filter(PostModel.id_user == id)
            .options(
                joinedload(PostModel.user),
                joinedload(PostModel.likes)
            )
            .order_by(PostModel.id.desc())
            .all()
        )

        if not posts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Posts not found"
            )
        response = []
        for p in posts:
            response.append({
                "id": p.id,
                "content": p.content,
                "url": p.url,
                "public_id": p.public_id,
                "created": p.created,
                "likes": [{"user_id": l.user_id} for l in p.likes],
                "user": {
                    "user_id": p.user.id,
                    "username": p.user.username,
                    "name": p.user.name,
                    "avatar_url": p.user.avatar_url
                }
            })

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



@root.delete('/delete/{id}')
async def delete_image(id: str ,current_user:UserModel = Depends(get_current_user), db:Session = Depends(get_db)):
    try:
        post = db.query(PostModel).filter(((PostModel.id_user == current_user.id) & (PostModel.id == id))).first()
        if not post:
            raise HTTPException(status_code=404, detail="Image not found or already deleted")
        
        if post.public_id:
        
            public_id = post.public_id
            
            image_cloudinary = api.resource(public_id)
            
            if not image_cloudinary:
                raise HTTPException(status_code=404, detail="Image not found or already deleted")
            
            result = uploader.destroy(public_id)
            
            if result.get("result") != "ok":
                raise HTTPException(status_code=404, detail="Image not found or already deleted")
        
        db.delete(post)
        db.commit()
        
        return {"message": "Post deleted successfully", "id": id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))