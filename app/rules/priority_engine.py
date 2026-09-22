"""
Explainable Operational Exception Prioritization Engine for SWITCHYARD.
Computes multi-factor priority scores (0-100) and priority bands (P1-P4)
from normalized risk dimensions with human-readable operational drivers.
"""
import math
from typing import List, Tuple
from app.core.config import settings
from app.models.schemas import PriorityBand, SLAStatus, CustomerTier, SeverityLevel


class ExplainablePriorityEngine:
    def __init__(
        self,
        weight_sla: float = None,
        weight_customer: float = None,
        weight_financial: float = None,
        weight_age: float = None,
        weight_criticality: float = None,
    ):
        self.w_sla = weight_sla if weight_sla is not None else settings.WEIGHT_SLA_RISK
        self.w_cust = weight_customer if weight_customer is not None else settings.WEIGHT_CUSTOMER_IMPACT
        self.w_fin = weight_financial if weight_financial is not None else settings.WEIGHT_FINANCIAL_IMPACT
        self.w_age = weight_age if weight_age is not None else settings.WEIGHT_CASE_AGE
        self.w_crit = weight_criticality if weight_criticality is not None else settings.WEIGHT_OPERATIONAL_CRITICALITY

        # Enforce sum of weights equals 1.0
        total_w = self.w_sla + self.w_cust + self.w_fin + self.w_age + self.w_crit
        if not math.isclose(total_w, 1.0, rel_tol=1e-3):
            raise ValueError(f"Priority weights must sum to 1.0, got {total_w}")

    def calculate_priority(
        self,
        sla_status: SLAStatus,
        sla_consumption_ratio: float,
        remaining_minutes: float,
        customer_tier: str,
        financial_exposure_usd: float,
        unassigned_hours: float,
        severity: str,
    ) -> Tuple[float, PriorityBand, List[str]]:
        """
        Calculates normalized score (0-100), assigns priority band, and produces explainable driver strings.
        """
        drivers = []

        # 1. SLA Score (0 - 100)
        if sla_status == SLAStatus.BREACHED:
            s_sla = 100.0
            drivers.append(f"SLA breached (overdue by {abs(remaining_minutes):.1f} min)")
        elif sla_status == SLAStatus.AT_RISK:
            s_sla = min(100.0, 80.0 + (sla_consumption_ratio - 0.80) * 100.0)
            drivers.append(f"SLA breach imminent in {max(0.0, remaining_minutes):.1f} minutes")
        else:
            s_sla = min(75.0, sla_consumption_ratio * 75.0)

        # 2. Customer Tier Score (0 - 100)
        tier_upper = customer_tier.upper()
        if CustomerTier.ENTERPRISE.value.upper() in tier_upper:
            s_cust = 100.0
            drivers.append("Tier 1 Enterprise customer account")
        elif CustomerTier.COMMERCIAL.value.upper() in tier_upper:
            s_cust = 60.0
        else:
            s_cust = 30.0

        # 3. Financial Exposure Score (Logarithmic scaling, $100k -> 100.0)
        exposure_clamped = max(1.0, financial_exposure_usd)
        s_fin = min(100.0, (math.log10(exposure_clamped) / 5.0) * 100.0)
        if financial_exposure_usd >= 25000:
            drivers.append(f"High financial exposure (${financial_exposure_usd:,.2f})")

        # 4. Case Age Score (Linear scale up to 24 hours)
        s_age = min(100.0, (unassigned_hours / 24.0) * 100.0)
        if unassigned_hours >= 4.0:
            drivers.append(f"Unassigned waiting time ({unassigned_hours:.1f} hrs) exceeds SLA triage standard")

        # 5. Operational Criticality Score
        sev_upper = severity.upper()
        if SeverityLevel.CRITICAL.value.upper() in sev_upper:
            s_crit = 100.0
            drivers.append("Mission-critical service failure")
        elif SeverityLevel.HIGH.value.upper() in sev_upper:
            s_crit = 75.0
        elif SeverityLevel.MEDIUM.value.upper() in sev_upper:
            s_crit = 40.0
        else:
            s_crit = 10.0

        # Weighted composite score
        composite_score = round(
            (self.w_sla * s_sla) +
            (self.w_cust * s_cust) +
            (self.w_fin * s_fin) +
            (self.w_age * s_age) +
            (self.w_crit * s_crit),
            2
        )
        composite_score = min(100.0, max(0.0, composite_score))

        # Priority Band Assignment
        if composite_score >= 85.0:
            band = PriorityBand.P1
        elif composite_score >= 70.0:
            band = PriorityBand.P2
        elif composite_score >= 45.0:
            band = PriorityBand.P3
        else:
            band = PriorityBand.P4

        if not drivers:
            drivers.append("Standard operational queue ranking")

        return composite_score, band, drivers
