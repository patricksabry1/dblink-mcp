#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dblink_mcp.providers.oracle import OracleConnector
from dblink_mcp.providers.postgres import PostgreSQLConnector
from dblink_mcp.providers.snowflake import SnowflakeConnector
from dblink_mcp.server import main
from dblink_mcp.services.comparison_service import DataComparator
from dblink_mcp.services.query_service import DatabaseManager
from dblink_mcp.services.testgen_service import TestGenerator

__all__ = [
    "main",
    "DatabaseManager",
    "DataComparator",
    "TestGenerator",
    "PostgreSQLConnector",
    "OracleConnector",
    "SnowflakeConnector",
]

if __name__ == "__main__":
    asyncio.run(main())
