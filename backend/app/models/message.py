import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin

class MessageRole(str, enum.Enum):
    user = 'user'
    assistant = 'assistant'

class Message(Base, TimestampMixin):
    __tablename__ = 'messages'

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.session_id'), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_slots: Mapped[dict] = mapped_column(JSONB, default=dict)