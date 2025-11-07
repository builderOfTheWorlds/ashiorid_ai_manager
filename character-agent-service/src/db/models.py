"""
Database models for Character Agent Service.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Character(Base):
    """Character personality model."""

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    universe = Column(String(50))
    system_prompt = Column(Text, nullable=False)
    traits = Column(JSON)
    preferred_model = Column(String(50))
    lore_collection = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Conversation(Base):
    """Conversation history model."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_name = Column(String(100), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    character_response = Column(Text, nullable=False)
    lore_sources = Column(JSON)  # List of lore sources used
    reasoning = Column(Text)  # Internal reasoning (optional)
    properties = Column(JSON)  # Additional properties (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_character_created', 'character_name', 'created_at'),
    )
