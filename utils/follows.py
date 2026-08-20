from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from models import FollowerModel, UserModel

def verify_follow(current_user:UserModel, second_user:int, db: Session):
  try:
      result = db.query(FollowerModel).filter(
          and_(
              FollowerModel.follower_id == current_user.id,
              FollowerModel.followed_id == second_user
          )
      ).first()

      print(current_user.id)

      return result is not None
  except Exception as error:
      print(error)
      return False

