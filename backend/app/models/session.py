import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin

class SessionStatus(str, enum.Enum):
    active = 'active'
    completed = 'completed'

class ChatSession(Base, TimestampMixin):
    __tablename__ = 'sessions'

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.active)