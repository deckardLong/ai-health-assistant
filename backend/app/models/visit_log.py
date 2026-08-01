import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, func, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin

class VisitLogType(str, enum.Enum):
    diagnosis = 'diagnosis'
    medication = 'medication'
    progression = 'progression'

class VisitLog(Base, TimestampMixin):
    __tablename__ = 'visit_logs'

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.session_id'), nullable=False
    )
    type: Mapped[VisitLogType] = mapped_column(Enum(VisitLogType), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)