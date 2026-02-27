from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class AddDatabaseConnectionInput(BaseModel):
    name: str = Field(description="Connection name")
    db_type: Literal["snowflake", "oracle", "postgresql"] = Field(description="Database type")
    config: Dict[str, Any] = Field(description="Database connection configuration")


class ExecuteQueryInput(BaseModel):
    connection_name: str = Field(description="Name of the database connection")
    query: str = Field(description="SQL query to execute")
    limit: int = Field(default=50, description="Optional row limit")


class CompareQueryResultsInput(BaseModel):
    connection1: str = Field(description="First database connection name")
    query1: str = Field(description="First query")
    connection2: str = Field(description="Second database connection name")
    query2: str = Field(description="Second query")


class DetectSchemaDifferencesInput(BaseModel):
    connection1: str = Field(description="First database connection name")
    query1: str = Field(description="First query")
    connection2: str = Field(description="Second database connection name")
    query2: str = Field(description="Second query")


class GenerateTestScriptInput(BaseModel):
    connection1: str = Field(description="First database connection name")
    query1: str = Field(description="First query")
    connection2: str = Field(description="Second database connection name")
    query2: str = Field(description="Second query")
    test_name: str = Field(default="test_data_comparison", description="Name for the test function")
