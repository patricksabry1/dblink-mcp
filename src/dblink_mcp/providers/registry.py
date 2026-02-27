from __future__ import annotations

from typing import Any, Callable, Dict, Type

from dblink_mcp.providers.base import DatabaseConnector
from dblink_mcp.providers.cassandra import CassandraConnector
from dblink_mcp.providers.oracle import OracleConnector
from dblink_mcp.providers.postgres import PostgreSQLConnector
from dblink_mcp.providers.redshift import RedshiftConnector
from dblink_mcp.providers.snowflake import SnowflakeConnector

ConnectorFactory = Callable[[Dict[str, Any]], DatabaseConnector]


class ConnectorRegistry:
    def __init__(self) -> None:
        self._factories: Dict[str, ConnectorFactory] = {}

    def register(self, name: str, connector_cls: Type[DatabaseConnector]) -> None:
        self._factories[name.lower()] = connector_cls

    def create(self, name: str, config: Dict[str, Any]) -> DatabaseConnector:
        factory = self._factories.get(name.lower())
        if not factory:
            raise ValueError(f"Unsupported database type: {name}")
        return factory(config)

    def has(self, name: str) -> bool:
        return name.lower() in self._factories


def build_default_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register("postgresql", PostgreSQLConnector)
    registry.register("postgres", PostgreSQLConnector)
    registry.register("oracle", OracleConnector)
    registry.register("snowflake", SnowflakeConnector)
    registry.register("redshift", RedshiftConnector)
    registry.register("cassandra", CassandraConnector)
    return registry
