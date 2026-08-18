import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = "12345678998765432"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
        
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    if not token or not isinstance(token, (str, bytes)):
        print("Error: El token proporcionado no es válido o está vacío.")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("Error: El token ha expirado")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Error: Token inválido ({e})")
        return None