"""
SLA State and Risk Evaluation Engine for SWITCHYARD.
Computes deterministic SLA target windows, elapsed and remaining minutes,
and evaluates status transitions (ON_TRACK, AT_RISK, BREACHED) using UTC timestamps.
"""
from datetime import datetime, timezone
from typing import Tuple, Dict, Any
from app.core.config import settings
from app.models.schemas import SLAStatus, SeverityLevel, CustomerTier


class SLAEngine:
    def __init__(
        self,
        warning_threshold_ratio: float = None,
        breach_threshold_ratio: float = None
    ):
        self.warning_threshold_ratio = warning_threshold_ratio or settings.SLA_WARNING_THRESHOLD_RATIO
        self.breach_threshold_ratio = breach_threshold_ratio or settings.SLA_BREACH_THRESHOLD_RATIO

    @staticmethod
    def calculate_target_minutes(customer_tier: str, severity: str, default_service_sla_min: int) -> int:
        """
        Determine target SLA minutes based on customer tier, severity, and service defaults.
        Enterprise accounts receive aggressive response windows.
        """
        if customer_tier == CustomerTier.ENTERPRISE.value:
            if severity == SeverityLevel.CRITICAL.value:
                return min(60, default_service_sla_min)
            elif severity == SeverityLevel.HIGH.value:
                return min(120, default_service_sla_min)
            return default_service_sla_min

        elif customer_tier == CustomerTier.COMMERCIAL.value:
            if severity == SeverityLevel.CRITICAL.value:
                return min(180, default_service_sla_min)
            return default_service_sla_min

        return default_service_sla_min

    def evaluate_sla_state(
        self,
        start_time: datetime,
        current_time: datetime,
        target_minutes: int
    ) -> Tuple[SLAStatus, float, float, float]:
        """
        Evaluate SLA state and return:
        (sla_status, elapsed_minutes, remaining_minutes, consumption_ratio)
        """
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Elapsed minutes (protected against negative time / clock skew)
        elapsed_seconds = max(0.0, (current_time - start_time).total_seconds())
        elapsed_minutes = round(elapsed_seconds / 60.0, 2)
        remaining_minutes = round(target_minutes - elapsed_minutes, 2)

        consumption_ratio = round(elapsed_minutes / max(1, target_minutes), 4)

        if consumption_ratio >= self.breach_threshold_ratio:
            status = SLAStatus.BREACHED
        elif consumption_ratio >= self.warning_threshold_ratio:
            status = SLAStatus.AT_RISK
        else:
            status = SLAStatus.ON_TRACK

        return status, elapsed_minutes, remaining_minutes, consumption_ratio
