from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from dblink_mcp.providers.base import DatabaseConnector

logger = logging.getLogger(__name__)


class PostgreSQLConnector(DatabaseConnector):
    async def connect(self) -> None:
        try:
            import psycopg2

            self.connection = psycopg2.connect(
                host=self.connection_config["host"],
                port=self.connection_config["port"],
                database=self.connection_config["database"],
                user=self.connection_config["user"],
                password=self.connection_config["password"],
            )
            logger.info("Connected to PostgreSQL")
        except ImportError as exc:
            raise ImportError("psycopg2 package is required for PostgreSQL connections") from exc

    async def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        return pd.read_sql(query, self.connection, params=params or {})
