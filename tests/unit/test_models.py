"""
Unit tests for Pydantic schemas, validation boundaries, and SQLAlchemy entities.
"""
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.models.schemas import (
    CustomerSchema,
    CustomerTier,
    ContractSLATier,
    ServiceSchema,
    LocationSchema,
    AgentSchema,
    OperationalEventSchema,
    SLARecordSchema,
    ExceptionRecordSchema,
    PriorityBand,
    ExceptionLifecycleState,
    SLAStatus
)

# 1. Customer Schema Tests
@pytest.mark.parametrize("tier,contract", [
    (CustomerTier.ENTERPRISE, ContractSLATier.GOLD),
    (CustomerTier.COMMERCIAL, ContractSLATier.SILVER),
    (CustomerTier.RETAIL, ContractSLATier.BRONZE),
])
def test_customer_schema_valid_tiers(tier, contract):
    c = CustomerSchema(
        customer_id="CUST-000001",
        customer_name="Test Enterprise Corp",
        tier=tier,
        contract_sla_tier=contract,
        industry="Finance"
    )
    assert c.tier == tier
    assert c.contract_sla_tier == contract


# 2. Service Schema Boundary Tests
@pytest.mark.parametrize("tier_level,sla_min,is_valid", [
    (1, 30, True),
    (2, 180, True),
    (3, 1440, True),
    (0, 60, False),    # tier_level < 1
    (4, 60, False),    # tier_level > 3
    (1, 0, False),     # default_sla_minutes <= 0
    (1, -10, False),   # negative sla
])
def test_service_schema_constraints(tier_level, sla_min, is_valid):
    if is_valid:
        s = ServiceSchema(
            service_id="SRV-0001",
            service_name="Test Srv",
            service_category="Core",
            tier_level=tier_level,
            default_sla_minutes=sla_min
        )
        assert s.tier_level == tier_level
    else:
        with pytest.raises(ValidationError):
            ServiceSchema(
                service_id="SRV-0001",
                service_name="Test Srv",
                service_category="Core",
                tier_level=tier_level,
                default_sla_minutes=sla_min
            )


# 3. Location Schema Tests
@pytest.mark.parametrize("region,country", [
    ("US-East", "USA"),
    ("US-West", "USA"),
    ("EU-Central", "Germany"),
    ("APAC-South", "India"),
])
def test_location_schema_regions(region, country):
    loc = LocationSchema(
        location_id="LOC-001",
        region=region,
        datacenter_zone="zone-a",
        country=country
    )
    assert loc.region == region
    assert loc.country == country


# 4. Agent Schema Tests
@pytest.mark.parametrize("skill,is_valid", [
    (1, True),
    (3, True),
    (5, True),
    (0, False),
    (6, False),
])
def test_agent_schema_skill_levels(skill, is_valid):
    if is_valid:
        agent = AgentSchema(
            agent_id="AGT-001",
            agent_name="Agent Smith",
            team_name="Triage",
            skill_level=skill,
            shift="Morning"
        )
        assert agent.skill_level == skill
    else:
        with pytest.raises(ValidationError):
            AgentSchema(
                agent_id="AGT-001",
                agent_name="Agent Smith",
                team_name="Triage",
                skill_level=skill,
                shift="Morning"
            )


# 5. Exception Record Schema Validation
def test_exception_record_schema_bounds():
    exc = ExceptionRecordSchema(
        exception_id="EXC-1",
        case_id="CASE-1",
        event_id="EVT-1",
        customer_id="CUST-1",
        service_id="SRV-1",
        location_id="LOC-1",
        financial_exposure=50000.0,
        priority_score=88.5,
        priority_band=PriorityBand.P1,
        lifecycle_state=ExceptionLifecycleState.DETECTED,
        reason_drivers=["Tier 1 Enterprise customer"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert exc.priority_score == 88.5
    assert exc.priority_band == "P1"

    # Score out of bounds (>100)
    with pytest.raises(ValidationError):
        ExceptionRecordSchema(
            exception_id="EXC-1",
            case_id="CASE-1",
            event_id="EVT-1",
            customer_id="CUST-1",
            service_id="SRV-1",
            location_id="LOC-1",
            financial_exposure=50000.0,
            priority_score=150.0,  # Invalid
            priority_band=PriorityBand.P1,
            lifecycle_state=ExceptionLifecycleState.DETECTED,
            reason_drivers=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
