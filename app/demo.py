"""
Deterministic one-command end-to-end demonstration runner for SWITCHYARD.
Executes synthetic generation, data-quality quarantine, Parquet partitioning,
operational serving load, SLA risk evaluation, and Max-Heap priority queue population.
"""
import argparse
from app.core.logging import logger
from pipelines.generate import run_generation
from pipelines.validate import run_validation
from pipelines.partition import ParquetPartitionPipeline
from pipelines.load import load_reference_data, load_operational_events
from app.repositories.database import init_db, get_db_context
from app.services.exception_service import OperationalExceptionService


def run_demo(scale: int = 1000, bad_data_rate: float = 0.03):
    logger.info("=================================================================")
    logger.info("===       SWITCHYARD OPERATIONAL WORKBENCH DEMO RUNNER        ===")
    logger.info("=================================================================")

    # Stage 1: Generate Synthetic Data
    logger.info(f"[1/5] Generating {scale} synthetic operational events (defect rate: {bad_data_rate*100:.1f}%)...")
    ref_data, events = run_generation(scale=scale, bad_data_rate=bad_data_rate)

    # Stage 2: Data Quality & Quarantine
    logger.info("[2/5] Ingesting and executing data-quality validation...")
    valid_records, metrics = run_validation()

    # Stage 3: Parquet Partitioning
    logger.info("[3/5] Transforming and writing date-partitioned Parquet files...")
    partition_pipeline = ParquetPartitionPipeline()
    partition_pipeline.transform_and_partition_events(valid_records)
    partition_pipeline.convert_reference_tables()

    # Stage 4: Relational Serving Database Load
    logger.info("[4/5] Loading operational serving tables (SQLite / PostgreSQL)...")
    init_db()
    load_reference_data()
    load_operational_events(valid_records)

    # Stage 5: SLA Risk & Explainable Priority Engine Execution
    logger.info("[5/5] Calculating SLA risks, evaluating priority scores, and populating Max-Heap queue...")
    with get_db_context() as db:
        service = OperationalExceptionService(db)
        processed = service.process_and_prioritize_exceptions(limit=500)
        kpis = service.get_summary_kpis()

    logger.info("=================================================================")
    logger.info("===                   DEMO EXECUTION SUMMARY                  ===")
    logger.info("=================================================================")
    logger.info(f"Total Operational Events Ingested:    {metrics['rows_processed']:,}")
    logger.info(f"Valid Records Partitioned to Parquet: {metrics['rows_valid']:,} ({metrics['acceptance_rate_pct']}%)")
    logger.info(f"Quarantined Anomalies (Audit Lake):   {metrics['rows_rejected']:,}")
    logger.info(f"Exceptions Prioritized into Backlog:  {kpis['total_exceptions']:,}")
    logger.info(f"Cases with SLA Breach / At-Risk:      {kpis['sla_breached_count']:,} / {kpis['sla_at_risk_count']:,}")
    logger.info(f"Active Backlog Queue Size:            {kpis['active_backlog']:,}")
    if kpis['highest_priority_exception']:
        top = kpis['highest_priority_exception']
        logger.info("-----------------------------------------------------------------")
        logger.info(f"Highest Priority Triage Case: {top['id']} (Score: {top['priority_score']}, Band: {top['priority_band']})")
        logger.info(f"Case SLA Status: {top['sla_status']} | Financial Exposure: ${top['financial_exposure']:,.2f}")
        logger.info("Driver Reasons:")
        for d in top['reason_drivers']:
            logger.info(f"  * {d}")
    logger.info("=================================================================")
    logger.info("Demonstration successfully prepared. You can now query the API:")
    logger.info("Run: python -m uvicorn app.api.main:app --port 8000")
    logger.info("=================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWITCHYARD End-to-End Demo Runner")
    parser.add_argument("--scale", type=int, default=1000, help="Number of operational events to generate")
    parser.add_argument("--bad-data-rate", type=float, default=0.03, help="Percentage of injected defects (e.g. 0.03 = 3 percent)")
    args = parser.parse_args()

    run_demo(scale=args.scale, bad_data_rate=args.bad_data_rate)
