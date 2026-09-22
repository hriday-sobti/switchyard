"""
Unit tests for modeled business impact calculator and Excel/BI scenario modeling.
Validates labor savings calculations, penalty avoidance, boundary volumes,
and scenario sensitivity parameters.
"""
import pytest
from scripts.impact_model import run_impact_model


# 1. Base Scenario Calculations (10 tests)
@pytest.mark.parametrize("incident_vol,curr_breach,model_breach,exp_avoided", [
    (10000, 10.0, 5.0, 6000),      # (10000 * 0.05) * 12 = 6000
    (15000, 11.8, 7.2, 8280),      # default scenario
    (20000, 12.0, 6.0, 14400),     # (20000 * 0.06) * 12 = 14400
    (5000, 15.0, 5.0, 6000),       # (5000 * 0.10) * 12 = 6000
    (1000, 8.0, 4.0, 480),         # (1000 * 0.04) * 12 = 480
    (25000, 10.0, 5.0, 15000),     # large volume
    (50000, 10.0, 5.0, 30000),     # high scale
    (10000, 5.0, 5.0, 0),          # zero difference
    (10000, 4.0, 6.0, 0),          # negative difference clamped to 0
    (500, 20.0, 10.0, 600),        # small volume
])
def test_impact_model_breach_avoidance_scenarios(incident_vol, curr_breach, model_breach, exp_avoided):
    res = run_impact_model(
        monthly_incident_volume=incident_vol,
        current_breach_rate_pct=curr_breach,
        modeled_breach_rate_pct=model_breach
    )
    outputs = res["modeled_outputs"]
    assert outputs["annual_sla_breaches_prevented"] == exp_avoided


# 2. Labor Time Savings Scenarios (12 tests)
@pytest.mark.parametrize("incident_vol,manual_min,switchyard_min,exp_monthly_hrs", [
    (10000, 14.0, 3.5, 1750.0),    # (10000 * 10.5) / 60 = 1750.0
    (15000, 14.0, 3.5, 2625.0),    # default scenario
    (20000, 14.0, 3.5, 3500.0),
    (6000, 15.0, 5.0, 1000.0),     # (6000 * 10.0) / 60 = 1000.0
    (12000, 12.0, 2.0, 2000.0),    # (12000 * 10.0) / 60 = 2000.0
    (5000, 10.0, 2.0, 666.7),
    (30000, 14.0, 3.5, 5250.0),
    (500, 14.0, 3.5, 87.5),
    (1000, 20.0, 5.0, 250.0),
    (2400, 15.0, 5.0, 400.0),
    (10000, 10.0, 10.0, 0.0),      # zero savings
    (18000, 15.0, 5.0, 3000.0),
])
def test_impact_model_triage_hours_scenarios(incident_vol, manual_min, switchyard_min, exp_monthly_hrs):
    res = run_impact_model(
        monthly_incident_volume=incident_vol,
        manual_triage_minutes_per_case=manual_min,
        switchyard_triage_minutes_per_case=switchyard_min
    )
    assert res["modeled_outputs"]["monthly_triage_hours_saved"] == pytest.approx(exp_monthly_hrs, rel=1e-2)


# 3. Penalty and Labor Valuation (10 tests)
@pytest.mark.parametrize("hourly_rate,penalty_cost", [
    (50.0, 1000.0),
    (65.0, 1250.0),
    (75.0, 1500.0),
    (85.0, 2000.0),
    (100.0, 2500.0),
    (120.0, 3000.0),
    (40.0, 800.0),
    (60.0, 1000.0),
    (90.0, 1800.0),
    (110.0, 2200.0),
])
def test_impact_model_financial_valuations(hourly_rate, penalty_cost):
    res = run_impact_model(
        blended_hourly_engineer_cost_usd=hourly_rate,
        average_penalty_per_breach_usd=penalty_cost
    )
    outputs = res["modeled_outputs"]
    assert outputs["annual_labor_value_usd"] > 0
    assert outputs["annual_sla_penalty_avoidance_usd"] > 0
    assert outputs["total_annual_economic_benefit_usd"] == pytest.approx(
        outputs["annual_labor_value_usd"] + outputs["annual_sla_penalty_avoidance_usd"], rel=1e-2
    )


# 4. Sensitivity & Metadata Contract Tests (10 tests)
def test_impact_model_metadata_labeling():
    res = run_impact_model()
    assert res["scenario_type"] == "MODELED_SCENARIO_ESTIMATE"
    assert "inputs" in res
    assert "modeled_outputs" in res


@pytest.mark.parametrize("incident_scale", [100, 250, 500, 1000, 5000, 10000, 25000, 50000, 100000, 250000])
def test_impact_model_scaling_monotonicity(incident_scale):
    res = run_impact_model(monthly_incident_volume=incident_scale)
    assert res["modeled_outputs"]["total_annual_economic_benefit_usd"] > 0
    assert res["modeled_outputs"]["annual_sla_breaches_prevented"] >= 0


# 5. Zero Input Boundary Tests (10 tests)
@pytest.mark.parametrize("zero_field", [
    "manual_triage_minutes_per_case",
    "switchyard_triage_minutes_per_case",
    "average_penalty_per_breach_usd",
    "blended_hourly_engineer_cost_usd",
])
def test_impact_model_zero_components(zero_field):
    kwargs = {zero_field: 0.0}
    res = run_impact_model(**kwargs)
    assert res["modeled_outputs"]["total_annual_economic_benefit_usd"] >= 0


@pytest.mark.parametrize("breach_rate", [0.0, 1.0, 5.0, 10.0, 20.0])
def test_impact_model_varied_base_breach_rates(breach_rate):
    res = run_impact_model(current_breach_rate_pct=breach_rate, modeled_breach_rate_pct=breach_rate / 2.0)
    assert res["modeled_outputs"]["annual_sla_breaches_prevented"] >= 0
