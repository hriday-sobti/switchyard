"""
Initial smoke test verifying framework configuration and logger setup.
"""
from app.core.config import settings
from app.core.logging import logger


def test_settings_loaded():
    assert settings.SWITCHYARD_ENV in ["development", "testing", "production"]
    assert settings.WEIGHT_SLA_RISK + settings.WEIGHT_CUSTOMER_IMPACT + settings.WEIGHT_FINANCIAL_IMPACT + settings.WEIGHT_CASE_AGE + settings.WEIGHT_OPERATIONAL_CRITICALITY == 1.0


def test_logger_setup():
    logger.info("Smoke test log entry executing successfully.")
    assert logger.name == "switchyard"
