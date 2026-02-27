from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pandas as pd

from dblink_mcp.providers.base import DatabaseConnector
from dblink_mcp.providers.registry import ConnectorRegistry, build_default_registry


class QueryService:
    def __init__(self, db_manager: "DatabaseManager") -> None:
        self.db_manager = db_manager

    async def execute_query(self, connection_name: str, query: str, limit: Optional[int] = 50) -> pd.DataFrame:
        connector = self.db_manager.get_connection(connection_name)
        query_to_run = query
        if limit:
            query_to_run = connector.apply_query_limit(query, limit)
        return await connector.execute_query(query_to_run)


class DatabaseManager:
    """Manages database connections with a registry-driven provider factory."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None):
        self.registry = registry or build_default_registry()
        self.connectors: Dict[str, DatabaseConnector] = {}

    @staticmethod
    def _resolve_config_with_env(config: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        resolved = config.copy()
        db_upper = db_type.upper()
        env_mappings = {
            "user": f"{db_upper}_USER",
            "password": f"{db_upper}_PASSWORD",
            "host": f"{db_upper}_HOST",
            "port": f"{db_upper}_PORT",
        }

        extras = {
            "snowflake": {
                "account": "SNOWFLAKE_ACCOUNT",
                "warehouse": "SNOWFLAKE_WAREHOUSE",
                "database": "SNOWFLAKE_DATABASE",
                "schema": "SNOWFLAKE_SCHEMA",
            },
            "oracle": {"service_name": "ORACLE_SERVICE_NAME"},
            "postgresql": {"database": "POSTGRESQL_DATABASE"},
            "postgres": {"database": "POSTGRES_DATABASE"},
            "redshift": {"database": "REDSHIFT_DATABASE"},
            "cassandra": {"keyspace": "CASSANDRA_KEYSPACE"},
        }
        env_mappings.update(extras.get(db_type.lower(), {}))

        for field, env_var in env_mappings.items():
            if resolved.get(field) is not None:
                continue
            env_value = os.getenv(env_var)
            if env_value is None:
                continue
            if field == "port":
                resolved[field] = int(env_value)
            else:
                resolved[field] = env_value

        return resolved

    async def add_connection(self, name: str, db_type: str, config: Dict[str, Any]) -> None:
        resolved_config = self._resolve_config_with_env(config, db_type)
        connector = self.registry.create(db_type, resolved_config)
        await connector.connect()
        self.connectors[name] = connector

    async def remove_connection(self, name: str) -> None:
        connector = self.connectors.get(name)
        if connector:
            await connector.disconnect()
            del self.connectors[name]

    def get_connection(self, name: str) -> DatabaseConnector:
        connector = self.connectors.get(name)
        if connector is None:
            raise ValueError(f"Connection '{name}' not found")
        return connector

    async def execute_query(self, connection_name: str, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        connector = self.get_connection(connection_name)
        return await connector.execute_query(query, params)
