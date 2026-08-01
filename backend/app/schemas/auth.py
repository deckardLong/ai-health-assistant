import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=8)
    dob: date | None = None
    gender: str | None = None
    consent_status: bool = Field(..., description='Bắt buộc đồng ý xử lý dữ liệu sức khỏe')

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    patient_id: uuid.UUID

class UserOut(BaseModel):
    user_id: uuid.UUID
    patient_id: uuid.UUID
    email: EmailStr
    role: str

    model_config = {'from_attributes': True}