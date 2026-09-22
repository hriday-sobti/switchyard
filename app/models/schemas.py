"""
Pydantic Schemas for operational entities, validation contracts, and events.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerTier(str, Enum):
    ENTERPRISE = "Enterprise"
    COMMERCIAL = "Commercial"
    RETAIL = "Retail"


class ContractSLATier(str, Enum):
    GOLD = "Gold"
    SILVER = "Silver"
    BRONZE = "Bronze"


class SLAStatus(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"


class PriorityBand(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ExceptionLifecycleState(str, Enum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# Dimension Models
class CustomerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str = Field(..., description="Canonical ID format: CUST-XXXXXX")
    customer_name: str
    tier: CustomerTier
    contract_sla_tier: ContractSLATier
    industry: str


class ServiceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_id: str = Field(..., description="Canonical ID format: SRV-XXXX")
    service_name: str
    service_category: str
    tier_level: int = Field(..., ge=1, le=3)
    default_sla_minutes: int = Field(..., gt=0)


class LocationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: str = Field(..., description="Canonical ID format: LOC-XXX-XX")
    region: str
    datacenter_zone: str
    country: str


class AgentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str = Field(..., description="Canonical ID format: AGT-XXXX")
    agent_name: str
    team_name: str
    skill_level: int = Field(..., ge=1, le=5)
    shift: str


# Operational Event Schema (Raw & Ingestion)
class OperationalEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime
    customer_id: str
    service_id: str
    location_id: str
    event_type: str
    duration_ms: Optional[int] = Field(None, ge=0)
    payload_bytes: Optional[int] = Field(None, ge=0)
    status_code: int = Field(..., ge=100, le=599)
    error_message: Optional[str] = None


# SLA Record Schema
class SLARecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sla_id: str
    case_id: str
    customer_id: str
    service_id: str
    start_time: datetime
    due_time: datetime
    target_minutes: int = Field(..., gt=0)
    elapsed_minutes: float = Field(..., ge=0)
    remaining_minutes: float
    sla_status: SLAStatus


# Exception Record Schema
class ExceptionRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exception_id: str
    case_id: str
    event_id: str
    customer_id: str
    service_id: str
    location_id: str
    financial_exposure: float = Field(..., ge=0.0)
    priority_score: float = Field(..., ge=0.0, le=100.0)
    priority_band: PriorityBand
    lifecycle_state: ExceptionLifecycleState
    reason_drivers: List[str]
    created_at: datetime
    updated_at: datetime
    assigned_team: Optional[str] = None
    assigned_agent: Optional[str] = None
