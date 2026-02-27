#!/usr/bin/env python3
import asyncio
import logging
from typing import Any, Optional, Dict
import pandas as pd
from abc import ABC, abstractmethod

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import ValidationError

from src.dblink_mcp.mcp.models import (
    AddDatabaseConnectionInput,
    CompareQueryResultsInput,
    DetectSchemaDifferencesInput,
    ExecuteQueryInput,
    GenerateTestScriptInput,
)
import json
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from dblink_mcp.server import *  # noqa: F401,F403

if __name__ == "__main__":
    import asyncio
    asyncio.run({test_name}())
'''
        return test_code

# Initialize the server
server = Server("dblink-mcp")
db_manager = DatabaseManager()

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="add_database_connection",
            description="Add a new database connection (Snowflake or Oracle)",
            inputSchema=AddDatabaseConnectionInput.model_json_schema(),
        ),
        Tool(
            name="execute_query",
            description="Execute a read-only query on a database connection",
            inputSchema=ExecuteQueryInput.model_json_schema(),
        ),
        Tool(
            name="compare_query_results",
            description="Compare results from two database queries",
            inputSchema=CompareQueryResultsInput.model_json_schema(),
        ),
        Tool(
            name="detect_schema_differences",
            description="Detect schema differences between query results",
            inputSchema=DetectSchemaDifferencesInput.model_json_schema(),
        ),
        Tool(
            name="generate_test_script",
            description="Generate a pytest test script for comparing query results",
            inputSchema=GenerateTestScriptInput.model_json_schema(),
        )
    ]


def _validation_error_response(tool_name: str, error: ValidationError) -> list[TextContent]:
    """Format pydantic validation errors into structured tool responses."""
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "error_type": "validation_error",
                    "tool": tool_name,
                    "message": "Invalid tool arguments",
                    "details": error.errors(),
                },
                indent=2,
            ),
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        if name == "add_database_connection":
            try:
                payload = AddDatabaseConnectionInput.model_validate(arguments)
            except ValidationError as error:
                return _validation_error_response(name, error)

            await db_manager.add_connection(payload.name, payload.db_type, payload.config)
            return [TextContent(type="text", text=f"Successfully added {payload.db_type} connection '{payload.name}'")]

        elif name == "execute_query":
            try:
                payload = ExecuteQueryInput.model_validate(arguments)
            except ValidationError as error:
                return _validation_error_response(name, error)

            query = payload.query

            # Add database-specific limit clause if not present
            if payload.limit and not any(keyword in query.upper() for keyword in ["LIMIT", "ROWNUM", "TOP"]):
                # Get the connector to determine database type
                if payload.connection_name in db_manager.connectors:
                    connector = db_manager.connectors[payload.connection_name]

                    # Apply database-specific limit syntax
                    if isinstance(connector, OracleConnector):
                        # Oracle uses ROWNUM - add to WHERE clause or create one
                        query_stripped = query.rstrip(';').strip()
                        if " WHERE " in query_stripped.upper():
                            query = f"{query_stripped} AND ROWNUM <= {payload.limit}"
                        else:
                            query = f"{query_stripped} WHERE ROWNUM <= {payload.limit}"
                    elif isinstance(connector, (SnowflakeConnector, PostgreSQLConnector)):
                        # Snowflake and PostgreSQL use LIMIT
                        query = f"{query.rstrip(';')} LIMIT {payload.limit}"

            df = await db_manager.execute_query(payload.connection_name, query)

            result = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_data": df.head(10).to_dict('records') if len(df) > 0 else []
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "compare_query_results":
            try:
                payload = CompareQueryResultsInput.model_validate(arguments)
            except ValidationError as error:
                return _validation_error_response(name, error)

            df1 = await db_manager.execute_query(payload.connection1, payload.query1)
            df2 = await db_manager.execute_query(payload.connection2, payload.query2)

            comparison = DataComparator.compare_dataframes(df1, df2, payload.connection1, payload.connection2)

            return [TextContent(type="text", text=json.dumps(comparison, indent=2))]

        elif name == "detect_schema_differences":
            try:
                payload = DetectSchemaDifferencesInput.model_validate(arguments)
            except ValidationError as error:
                return _validation_error_response(name, error)

            df1 = await db_manager.execute_query(payload.connection1, payload.query1)
            df2 = await db_manager.execute_query(payload.connection2, payload.query2)

            differences = DataComparator.detect_schema_differences(df1, df2)

            return [TextContent(type="text", text=json.dumps(differences, indent=2))]

        elif name == "generate_test_script":
            try:
                payload = GenerateTestScriptInput.model_validate(arguments)
            except ValidationError as error:
                return _validation_error_response(name, error)

            test_code = TestGenerator.generate_comparison_test(
                payload.connection1, payload.query1, payload.connection2, payload.query2, payload.test_name
            )

            return [TextContent(type="text", text=test_code)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error in tool '{name}': {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dblink-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
