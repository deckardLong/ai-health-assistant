import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.mixins import TimestampMixin

class UserRole(str, enum.Enum):
    patient = 'patient'
    doctor = 'doctor'
    admin = 'admin'

class User(Base, TimestampMixin):
    __tablename__ = 'users'

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.patient)
    consent_status: Mapped[bool] = mapped_column(Boolean, default=False)

    patient = relationship('Patient', back_populates='user')