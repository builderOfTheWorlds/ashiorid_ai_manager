"""Database models for Simulation Engine."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Agent(Base):
    """Agent model."""
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    state = Column(String(20), nullable=False, index=True)
    position_x = Column(Integer, nullable=False)
    position_y = Column(Integer, nullable=False)
    hunger = Column(Float, default=0.5)
    thirst = Column(Float, default=0.5)
    energy = Column(Float, default=1.0)
    health = Column(Float, default=1.0)
    age = Column(Integer, default=0)
    inventory = Column(JSON, default=list)
    properties = Column(JSON)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index('idx_agent_state_position', 'state', 'position_x', 'position_y'),)

class SimulationEvent(Base):
    """Simulation event model."""
    __tablename__ = "simulation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    description = Column(String(500))
    agent_ids = Column(JSON)
    location_x = Column(Integer)
    location_y = Column(Integer)
    properties = Column(JSON)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
