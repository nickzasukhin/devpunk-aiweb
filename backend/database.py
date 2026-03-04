import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Boolean, DateTime, Text,
    Enum, Integer, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

from config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RoleEnum(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"


class ChannelEnum(str, enum.Enum):
    text = "text"
    voice = "voice"


class AgentEnum(str, enum.Enum):
    sales = "sales"
    voice = "voice"


class MessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"


# ─── Admin Users ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.admin)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    audit_logs = relationship("AuditLog", back_populates="user")


# ─── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


# ─── Config (key-value store for agent settings) ──────────────────────────────

class Config(Base):
    __tablename__ = "config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


# ─── Documents ────────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="indexed")  # indexed | processing | error
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


# ─── Visitors ─────────────────────────────────────────────────────────────────

class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anonymous_id = Column(String(36), unique=True, nullable=False, index=True)
    fingerprint = Column(String(512), nullable=True, index=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, nullable=True)

    conversations = relationship("Conversation", back_populates="visitor")


# ─── Conversations ─────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("visitors.id"), nullable=False)
    channel = Column(Enum(ChannelEnum), nullable=False, default=ChannelEnum.text)
    agent = Column(Enum(AgentEnum), nullable=False, default=AgentEnum.sales)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    audio_url = Column(Text, nullable=True)

    visitor = relationship("Visitor", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.timestamp")


# ─── Messages ──────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(Enum(MessageRoleEnum), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tokens_used = Column(Integer, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)
