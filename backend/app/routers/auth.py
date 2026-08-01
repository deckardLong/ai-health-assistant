from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/register', response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if not payload.consent_status:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Cần đồng ý xử lý dữ liệu sức khỏe')

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, 'Email đã được sử dụng')

    patient = Patient(dob=payload.dob, gender=payload.gender)
    db.add(patient)
    db.flush() # to have patient.patient_id before creating User

    user = User(
        patient_id=patient.patient_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        consent_status=payload.consent_status
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        'sub': str(user.user_id),
        'patient_id': str(user.patient_id),
        'role': user.role.value
    })
    return TokenResponse(access_token=token, patient_id=user.patient_id)

@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Email hoặc mật khẩu không đúng')

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Email hoặc mật khẩu không đúng')

    token = create_access_token({
        'sub': str(user.user_id),
        'patient_id': str(user.patient_id),
        'role': user.role.value
    })
    return TokenResponse(access_token=token, patient_id=user.patient_id)

@router.get('/me', response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user