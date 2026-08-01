import uuid
from datetime import datetime, date
from sqlalchemy import DateTime, Date, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.mixins import TimestampMixin

class Patient(Base, TimestampMixin):
    __tablename__ = 'patients'

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    chronic_conditions: Mapped[dict] = mapped_column(JSONB, default=dict)
    allergies: Mapped[dict] = mapped_column(JSONB, default=dict)

    user = relationship('User', back_populates='patient', uselist=False)