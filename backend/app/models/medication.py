import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, func, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin

class MedicationStatus(str, enum.Enum):
    active = 'active'
    stopped = 'stopped'

class Medication(Base, TimestampMixin):
    __tablename__ = 'medications'

    medication_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.session_id'), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=True)
    schedule: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[MedicationStatus] = mapped_column(Enum(MedicationStatus), default=MedicationStatus.active)
    prescribed_by: Mapped[str] = mapped_column(String(100), nullable=True)