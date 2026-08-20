from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from models import (
    PostModel,
    UserModel,
    FollowerModel,
    NotificationModel,
)
from config import get_db
from security import get_current_user
from cloudinary import uploader, api

from schemas import PostCreate

root = APIRouter(
    prefix="/api/v1/post",
    tags=["Post"]
)


@root.post("/create")
async def create_post(
    data: PostCreate,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(authorization, db)

    if not data.content and not data.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El post debe tener texto o una imagen."
        )

    try:
        image_url = None
        public_id = None

        if data.image_base64:

            try:

                result = uploader.upload(
                    data.image_base64,
                    resource_type="image"
                )

                image_url = result.get("secure_url")
                public_id = result.get("public_id")

                if not image_url or not public_id:
                    raise HTTPException(
                        status_code=500,
                        detail="Cloudinary no devolvió los datos esperados."
                    )

            except Exception as upload_error:

                print(
                    f"❌ Error subiendo imagen a Cloudinary: "
                    f"{upload_error}"
                )

                raise HTTPException(
                    status_code=500,
                    detail=f"Error subiendo imagen: {str(upload_error)}"
                )

        post = PostModel(
            id_user=current_user.id,
            content=data.content,
            url=image_url,
            public_id=public_id
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        try:

            following_ids = (
                db.query(FollowerModel.followed_id)
                .filter(
                    FollowerModel.follower_id == current_user.id
                )
                .all()
            )

            for id_tuple in following_ids:

                followed_id = id_tuple[0]

                new_notification = NotificationModel(
                    user_id=followed_id,
                    other_user_id=current_user.id,
                    content="ha subido un nuevo post!"
                )

                db.add(new_notification)

            db.commit()

        except Exception as notification_error:

            print(
                "⚠️ Error creando notificaciones:",
                notification_error
            )

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

        db.rollback()

        print(
            f"❌ Error crítico creando post: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error creando post: {str(e)}"
        )


@root.get("/{id}")
def get_posts_current_user(
    id: int,
    db: Session = Depends(get_db)
):

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
        return []

    response = []

    for post in posts:

        response.append({

            "id": post.id,

            "content": post.content,

            "url": post.url,

            "public_id": post.public_id,

            "created": post.created,

            "likes": [
                {
                    "user_id": like.user_id
                }
                for like in post.likes
            ],

            "user": {

                "user_id": post.user.id,

                "username": post.user.username,

                "name": post.user.name,

                "avatar_url": post.user.avatar_url
            }
        })

    return response



@root.delete("/delete/{id}")
async def delete_post(
    id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        post = (
            db.query(PostModel)
            .filter(
                PostModel.id == id,
                PostModel.id_user == current_user.id
            )
            .first()
        )

        if not post:

            raise HTTPException(
                status_code=404,
                detail="Post no encontrado."
            )

        if post.public_id:

            try:

                result = uploader.destroy(
                    post.public_id,
                    resource_type="image"
                )

                print(
                    "🗑️ Cloudinary:",
                    result
                )

            except Exception as cloudinary_error:

                print(
                    "⚠️ No se pudo eliminar "
                    "la imagen de Cloudinary:",
                    cloudinary_error
                )

        db.delete(post)

        db.commit()

        return {
            "message": "Post eliminado correctamente",
            "id": id
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        print(
            f"❌ Error eliminando post: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando post: {str(e)}"
        )

    