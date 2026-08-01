from datetime import datetime, timedelta, timezone
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext    
from app.core.config import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def hash_password(plain_password):
    return pwd_context.hash(plain_password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data, expires_minutes):
    to_encode = data.copy()

    if expires_minutes is None:
        expires_minutes = settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({'exp': expire})

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token):
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError:
        raise ValueError('Token đã hết hạn')
    except JWTError:
        raise ValueError('Token không hợp lệ')