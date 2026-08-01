import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin

class TriageLevel(str, enum.Enum):
    self_monitor = 'self_monitor'
    see_doctor = 'see_doctor'
    emergency = 'emergency'

class Diagnosis(Base, TimestampMixin):
    __tablename__ = 'diagnoses'

    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.session_id'), nullable=False
    )
    differential_list: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_votes: Mapped[dict] = mapped_column(JSONB, default=dict)
    triage_level: Mapped[TriageLevel] = mapped_column(Enum(TriageLevel), nullable=False)