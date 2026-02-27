import json
from unittest.mock import AsyncMock, patch

import pytest

from server import handle_call_tool, handle_list_tools
from src.dblink_mcp.mcp.models import AddDatabaseConnectionInput


@pytest.mark.asyncio
async def test_tool_input_schema_comes_from_pydantic_models():
    tools = await handle_list_tools()
    add_connection_tool = next(tool for tool in tools if tool.name == "add_database_connection")

    assert add_connection_tool.inputSchema == AddDatabaseConnectionInput.model_json_schema()


@pytest.mark.asyncio
async def test_tool_validation_error_is_structured_json():
    result = await handle_call_tool("execute_query", {"connection_name": "test_conn"})

    payload = json.loads(result[0].text)
    assert payload["error_type"] == "validation_error"
    assert payload["tool"] == "execute_query"
    assert payload["message"] == "Invalid tool arguments"
    assert payload["details"]


@pytest.mark.asyncio
async def test_add_connection_uses_validated_payload():
    with patch("server.db_manager.add_connection", new_callable=AsyncMock) as mocked_add:
        result = await handle_call_tool(
            "add_database_connection",
            {
                "name": "demo_conn",
                "db_type": "postgresql",
                "config": {"host": "localhost", "port": 5432, "database": "app", "user": "u", "password": "p"},
            },
        )

    mocked_add.assert_awaited_once_with(
        "demo_conn",
        "postgresql",
        {"host": "localhost", "port": 5432, "database": "app", "user": "u", "password": "p"},
    )
    assert "Successfully added postgresql connection 'demo_conn'" in result[0].text
