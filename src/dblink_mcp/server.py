from __future__ import annotations

import asyncio
import json
import logging

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from dblink_mcp.services.comparison_service import DataComparator
from dblink_mcp.services.query_service import DatabaseManager, QueryService
from dblink_mcp.services.testgen_service import TestGenerator

logger = logging.getLogger(__name__)

server = Server("dblink-mcp")
db_manager = DatabaseManager()
query_service = QueryService(db_manager)
comparison_service = DataComparator()
testgen_service = TestGenerator()


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="add_database_connection",
            description="Add a new database connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "db_type": {"type": "string"},
                    "config": {"type": "object"},
                },
                "required": ["name", "db_type", "config"],
            },
        ),
        Tool(
            name="execute_query",
            description="Execute read-only query on configured database connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_name": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["connection_name", "query"],
            },
        ),
        Tool(
            name="compare_query_results",
            description="Compare results from two queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string"},
                    "query1": {"type": "string"},
                    "connection2": {"type": "string"},
                    "query2": {"type": "string"},
                },
                "required": ["connection1", "query1", "connection2", "query2"],
            },
        ),
        Tool(
            name="detect_schema_differences",
            description="Detect schema differences between two queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string"},
                    "query1": {"type": "string"},
                    "connection2": {"type": "string"},
                    "query2": {"type": "string"},
                },
                "required": ["connection1", "query1", "connection2", "query2"],
            },
        ),
        Tool(
            name="generate_test_script",
            description="Generate a pytest test script for comparing query results",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string"},
                    "query1": {"type": "string"},
                    "connection2": {"type": "string"},
                    "query2": {"type": "string"},
                    "test_name": {"type": "string", "default": "test_data_comparison"},
                },
                "required": ["connection1", "query1", "connection2", "query2"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "add_database_connection":
            await db_manager.add_connection(arguments["name"], arguments["db_type"], arguments["config"])
            text = f"Successfully added {arguments['db_type']} connection '{arguments['name']}'"
            return [TextContent(type="text", text=text)]

        if name == "execute_query":
            df = await query_service.execute_query(
                arguments["connection_name"],
                arguments["query"],
                arguments.get("limit", 50),
            )
            result = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_data": df.head(10).to_dict("records") if len(df) > 0 else [],
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "compare_query_results":
            df1 = await db_manager.execute_query(arguments["connection1"], arguments["query1"])
            df2 = await db_manager.execute_query(arguments["connection2"], arguments["query2"])
            result = comparison_service.compare_dataframes(df1, df2, arguments["connection1"], arguments["connection2"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "detect_schema_differences":
            df1 = await db_manager.execute_query(arguments["connection1"], arguments["query1"])
            df2 = await db_manager.execute_query(arguments["connection2"], arguments["query2"])
            result = comparison_service.detect_schema_differences(df1, df2)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "generate_test_script":
            code = testgen_service.generate_comparison_test(
                arguments["connection1"],
                arguments["query1"],
                arguments["connection2"],
                arguments["query2"],
                arguments.get("test_name", "test_data_comparison"),
            )
            return [TextContent(type="text", text=code)]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as exc:
        logger.exception("Error in tool '%s'", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def main() -> None:
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
