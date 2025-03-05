from sqlalchemy import Boolean, Column, ForeignKey, String, DateTime, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    subscription_tier = Column(String, default='free')
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_paid(self):
        """Check if user has a paid subscription"""
        return self.subscription_tier != 'free'

class Query(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    query_text = Column(Text, nullable=False)
    signals_to_track = Column(JSONB)
    is_paused = Column(Boolean, default=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    check_frequency_hours = Column(Integer, default=24)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="queries")
    leads = relationship("Lead", back_populates="query", cascade="all, delete-orphan")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey('queries.id'), nullable=False)
    company_name = Column(String)
    website = Column(String)
    employee_name = Column(String)
    employee_linkedin = Column(String)
    employee_email = Column(String)
    signals = Column(JSON)
    reasoning = Column(Text)
    is_checked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    query = relationship("Query", back_populates="leads")