from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from jose import JWTError, ExpiredSignatureError

bearer_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(credentials.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Token đã hết hạn')
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Token không hợp lệ')

    user = db.get(User, payload.get('sub'))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Người dùng không tồn tại')
    return user