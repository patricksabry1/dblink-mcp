from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from dblink_mcp.providers.base import DatabaseConnector

logger = logging.getLogger(__name__)


class OracleConnector(DatabaseConnector):
    async def connect(self) -> None:
        try:
            import cx_Oracle

            dsn = cx_Oracle.makedsn(
                self.connection_config["host"],
                self.connection_config["port"],
                service_name=self.connection_config["service_name"],
            )
            self.connection = cx_Oracle.connect(
                user=self.connection_config["user"],
                password=self.connection_config["password"],
                dsn=dsn,
            )
            logger.info("Connected to Oracle")
        except ImportError as exc:
            raise ImportError("cx_Oracle package is required for Oracle connections") from exc

    async def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Oracle")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        return pd.read_sql(query, self.connection, params=params or {})

    def apply_query_limit(self, query: str, limit: int) -> str:
        if any(keyword in query.upper() for keyword in ["LIMIT", "ROWNUM", "TOP"]):
            return query
        query_stripped = query.rstrip(";").strip()
        if " WHERE " in query_stripped.upper():
            return f"{query_stripped} AND ROWNUM <= {limit}"
        return f"{query_stripped} WHERE ROWNUM <= {limit}"
