"""
Modeled Business Impact & Operational Economics Simulator for SWITCHYARD.
Computes scenario-based estimates of operational hours saved, SLA breach penalty reductions,
and triage efficiency gains using explicit, configurable assumptions.
"""
import argparse
from typing import Dict, Any


def run_impact_model(
    monthly_incident_volume: int = 15000,
    current_breach_rate_pct: float = 11.8,
    modeled_breach_rate_pct: float = 7.2,
    manual_triage_minutes_per_case: float = 14.0,
    switchyard_triage_minutes_per_case: float = 3.5,
    average_penalty_per_breach_usd: float = 1250.0,
    blended_hourly_engineer_cost_usd: float = 65.0
) -> Dict[str, Any]:
    """
    Simulate operational savings and SLA penalty reductions.
    NOTE: All outputs are explicitly modeled/scenario-based estimates.
    """
    # 1. Triage Labor Efficiency
    monthly_manual_triage_hours = (monthly_incident_volume * manual_triage_minutes_per_case) / 60.0
    monthly_switchyard_triage_hours = (monthly_incident_volume * switchyard_triage_minutes_per_case) / 60.0
    monthly_hours_saved = monthly_manual_triage_hours - monthly_switchyard_triage_hours
    annual_hours_saved = monthly_hours_saved * 12.0
    annual_labor_savings_usd = annual_hours_saved * blended_hourly_engineer_cost_usd

    # 2. SLA Penalty Reductions
    current_monthly_breaches = monthly_incident_volume * (current_breach_rate_pct / 100.0)
    modeled_monthly_breaches = monthly_incident_volume * (modeled_breach_rate_pct / 100.0)
    monthly_breaches_avoided = max(0.0, current_monthly_breaches - modeled_monthly_breaches)
    annual_breaches_avoided = monthly_breaches_avoided * 12.0
    annual_penalty_savings_usd = annual_breaches_avoided * average_penalty_per_breach_usd

    # Total Modeled Economic Benefit
    total_annual_modeled_benefit_usd = annual_labor_savings_usd + annual_penalty_savings_usd

    return {
        "scenario_type": "MODELED_SCENARIO_ESTIMATE",
        "inputs": {
            "monthly_incident_volume": monthly_incident_volume,
            "current_breach_rate_pct": current_breach_rate_pct,
            "modeled_breach_rate_pct": modeled_breach_rate_pct,
            "manual_triage_minutes": manual_triage_minutes_per_case,
            "switchyard_triage_minutes": switchyard_triage_minutes_per_case,
            "penalty_per_breach_usd": average_penalty_per_breach_usd,
            "engineer_hourly_cost_usd": blended_hourly_engineer_cost_usd,
        },
        "modeled_outputs": {
            "monthly_triage_hours_saved": round(monthly_hours_saved, 1),
            "annual_triage_hours_saved": round(annual_hours_saved, 1),
            "annual_labor_value_usd": round(annual_labor_savings_usd, 2),
            "annual_sla_breaches_prevented": int(annual_breaches_avoided),
            "annual_sla_penalty_avoidance_usd": round(annual_penalty_savings_usd, 2),
            "total_annual_economic_benefit_usd": round(total_annual_modeled_benefit_usd, 2),
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWITCHYARD Modeled Economic Impact Calculator")
    args = parser.parse_args()

    results = run_impact_model()
    print("\n=== SWITCHYARD MODELED BUSINESS IMPACT (SIMULATION) ===")
    print(f"Annual Triage Hours Reclaimed: {results['modeled_outputs']['annual_triage_hours_saved']:,.1f} hrs")
    print(f"Annual Labor Productivity Value: ${results['modeled_outputs']['annual_labor_value_usd']:,.2f}")
    print(f"Annual SLA Breaches Prevented: {results['modeled_outputs']['annual_sla_breaches_prevented']:,} cases")
    print(f"Annual Penalty Avoidance: ${results['modeled_outputs']['annual_sla_penalty_avoidance_usd']:,.2f}")
    print(f"Total Modeled Annual Economic Benefit: ${results['modeled_outputs']['total_annual_economic_benefit_usd']:,.2f}")
    print("======================================================\n")
