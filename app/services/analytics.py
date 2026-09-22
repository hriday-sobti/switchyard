"""
DuckDB analytics service executing analytical queries directly against partitioned Parquet files.
Handles reliability metrics, bottleneck ranking, and hourly error rates.
"""
from pathlib import Path
from typing import List, Dict, Any
import duckdb
from app.core.config import settings
from app.core.logging import logger


class DuckDBAnalyticsService:
    def __init__(self, processed_dir: Path = None):
        self.processed_dir = processed_dir or settings.DATA_PROCESSED_DIR
        self.con = duckdb.connect(database=":memory:")
        self._register_views()

    def _register_views(self):
        """Register Parquet files as relational views in DuckDB."""
        events_path = str(self.processed_dir / "fact_operational_event" / "**" / "*.parquet").replace("\\", "/")
        cust_path = str(self.processed_dir / "dim_customers.parquet").replace("\\", "/")
        srv_path = str(self.processed_dir / "dim_services.parquet").replace("\\", "/")
        loc_path = str(self.processed_dir / "dim_locations.parquet").replace("\\", "/")

        self.con.execute(f"CREATE OR REPLACE VIEW fact_operational_event AS SELECT * FROM read_parquet('{events_path}', hive_partitioning=true);")
        self.con.execute(f"CREATE OR REPLACE VIEW dim_customer AS SELECT * FROM read_parquet('{cust_path}');")
        self.con.execute(f"CREATE OR REPLACE VIEW dim_service AS SELECT * FROM read_parquet('{srv_path}');")
        self.con.execute(f"CREATE OR REPLACE VIEW dim_location AS SELECT * FROM read_parquet('{loc_path}');")

        # Load SQL analytical view definitions
        views_sql = Path("sql/analytics/views.sql").read_text(encoding="utf-8")
        self.con.execute(views_sql)

    def get_service_reliability_metrics(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM vw_service_reliability_summary ORDER BY error_rate_pct DESC"
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_location_bottlenecks(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM vw_location_bottlenecks ORDER BY failure_rank ASC"
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_hourly_incident_trend(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            hour,
            COUNT(*) AS total_events,
            SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS error_events
        FROM fact_operational_event
        GROUP BY hour
        ORDER BY hour ASC
        """
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")
