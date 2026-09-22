"""
Unit tests for deterministic synthetic data generation.
"""
from pipelines.generate import SyntheticDataGenerator


def test_synthetic_generator_deterministic_seed():
    gen1 = SyntheticDataGenerator(seed=123, bad_data_rate=0.0)
    gen2 = SyntheticDataGenerator(seed=123, bad_data_rate=0.0)

    ref1 = gen1.generate_reference_data(customer_count=10)
    ref2 = gen2.generate_reference_data(customer_count=10)

    assert ref1["customers"] == ref2["customers"]

    events1 = gen1.generate_operational_stream(ref1, event_count=50)
    events2 = gen2.generate_operational_stream(ref2, event_count=50)

    assert events1 == events2


def test_synthetic_generator_bad_data_injection():
    gen = SyntheticDataGenerator(seed=42, bad_data_rate=0.50)  # High rate to guarantee defects
    ref = gen.generate_reference_data(customer_count=10)
    events = gen.generate_operational_stream(ref, event_count=100)

    # Check for presence of at least one defect
    has_defect = any(
        e["customer_id"] is None or
        e["status_code"] == 999 or
        (e["duration_ms"] is not None and e["duration_ms"] < 0) or
        e["service_id"] == "SRV-NONEXISTENT-9999"
        for e in events
    )
    assert has_defect is True
