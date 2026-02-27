from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from dblink_mcp.providers.base import DatabaseConnector

logger = logging.getLogger(__name__)


class SnowflakeConnector(DatabaseConnector):
    async def connect(self) -> None:
        try:
            import snowflake.connector

            self.connection = snowflake.connector.connect(
                user=self.connection_config["user"],
                password=self.connection_config["password"],
                account=self.connection_config["account"],
                warehouse=self.connection_config.get("warehouse"),
                database=self.connection_config.get("database"),
                schema=self.connection_config.get("schema"),
            )
            logger.info("Connected to Snowflake")
        except ImportError as exc:
            raise ImportError("snowflake-connector-python package is required for Snowflake connections") from exc

    async def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or {})
            return cursor.fetch_pandas_all()
        finally:
            cursor.close()
