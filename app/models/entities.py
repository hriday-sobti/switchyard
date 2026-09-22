"""
SQLAlchemy ORM Entities for operational serving database.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Customer(Base):
    __tablename__ = "dim_customer"

    customer_id = Column(String(32), primary_key=True)
    customer_name = Column(String(128), nullable=False)
    tier = Column(String(16), nullable=False)
    contract_sla_tier = Column(String(16), nullable=False)
    industry = Column(String(64), nullable=False)


class Service(Base):
    __tablename__ = "dim_service"

    service_id = Column(String(32), primary_key=True)
    service_name = Column(String(128), nullable=False)
    service_category = Column(String(32), nullable=False)
    tier_level = Column(Integer, nullable=False)
    default_sla_minutes = Column(Integer, nullable=False)


class Location(Base):
    __tablename__ = "dim_location"

    location_id = Column(String(32), primary_key=True)
    region = Column(String(32), nullable=False)
    datacenter_zone = Column(String(32), nullable=False)
    country = Column(String(32), nullable=False)


class OperationalEvent(Base):
    __tablename__ = "fact_operational_event"

    event_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    customer_id = Column(String(32), ForeignKey("dim_customer.customer_id"), nullable=False, index=True)
    service_id = Column(String(32), ForeignKey("dim_service.service_id"), nullable=False, index=True)
    location_id = Column(String(32), ForeignKey("dim_location.location_id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    payload_bytes = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)


class SLARecord(Base):
    __tablename__ = "fact_sla_record"

    sla_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    customer_id = Column(String(32), ForeignKey("dim_customer.customer_id"), nullable=False)
    service_id = Column(String(32), ForeignKey("dim_service.service_id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    due_time = Column(DateTime, nullable=False)
    target_minutes = Column(Integer, nullable=False)
    elapsed_minutes = Column(Float, nullable=False)
    remaining_minutes = Column(Float, nullable=False)
    sla_status = Column(String(16), nullable=False, index=True)


class ExceptionRecord(Base):
    __tablename__ = "fact_exception"

    exception_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    event_id = Column(String(64), ForeignKey("fact_operational_event.event_id"), nullable=False)
    customer_id = Column(String(32), ForeignKey("dim_customer.customer_id"), nullable=False, index=True)
    service_id = Column(String(32), ForeignKey("dim_service.service_id"), nullable=False, index=True)
    location_id = Column(String(32), ForeignKey("dim_location.location_id"), nullable=False, index=True)
    financial_exposure = Column(Float, nullable=False)
    priority_score = Column(Float, nullable=False, index=True)
    priority_band = Column(String(4), nullable=False, index=True)
    lifecycle_state = Column(String(16), nullable=False, index=True)
    reason_drivers = Column(Text, nullable=False)  # JSON serialized list of driver strings
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_team = Column(String(64), nullable=True)
    assigned_agent = Column(String(64), nullable=True)


Index("idx_exception_priority_lifecycle", ExceptionRecord.priority_score.desc(), ExceptionRecord.lifecycle_state)
Index("idx_sla_status_due", SLARecord.sla_status, SLARecord.due_time)
