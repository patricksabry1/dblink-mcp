from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from dblink_mcp.providers.base import DatabaseConnector

logger = logging.getLogger(__name__)


class CassandraConnector(DatabaseConnector):
    async def connect(self) -> None:
        try:
            from cassandra.cluster import Cluster

            cluster = Cluster(
                [self.connection_config["host"]],
                port=self.connection_config.get("port", 9042),
            )
            self.connection = cluster.connect(self.connection_config.get("keyspace"))
            logger.info("Connected to Cassandra")
        except ImportError as exc:
            raise ImportError("cassandra-driver package is required for Cassandra connections") from exc

    async def disconnect(self) -> None:
        if self.connection:
            cluster = self.connection.cluster
            self.connection.shutdown()
            cluster.shutdown()
            logger.info("Disconnected from Cassandra")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        result = self.connection.execute(query, parameters=params)
        return pd.DataFrame(list(result))
