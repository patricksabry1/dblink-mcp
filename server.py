#!/usr/bin/env python3
import asyncio
import logging
from typing import Any, Optional, Dict, List, Union
import pandas as pd
from abc import ABC, abstractmethod

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CompleteCompletionRequestParams,
    GetPromptRequestParams,
    ListPromptsRequestParams,
    ListResourcesRequestParams,
    ListToolsRequestParams,
    LoggingLevel,
    PromptRequestParams,
    ReadResourceRequestParams,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import AnyUrl
import json
import os

logger = logging.getLogger(__name__)

class DatabaseConnector(ABC):
    """Abstract base class for synchronous database connectors.

    Connector implementations are intentionally blocking and should only be
    invoked from the async service layer via ``DatabaseManager._run_blocking``.
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        self.connection_config = connection_config
        self.connection = None
    
    @abstractmethod
    def connect(self):
        """Establish database connection"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close database connection"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute a read-only query and return results as DataFrame"""
        pass
    
    @abstractmethod
    def validate_readonly_query(self, query: str) -> bool:
        """Validate that query is read-only"""
        pass

class SnowflakeConnector(DatabaseConnector):
    """Snowflake database connector"""
    
    def connect(self):
        try:
            import snowflake.connector
            from snowflake.connector.pandas_tools import pd_writer
            
            self.connection = snowflake.connector.connect(
                user=self.connection_config['user'],
                password=self.connection_config['password'],
                account=self.connection_config['account'],
                warehouse=self.connection_config.get('warehouse'),
                database=self.connection_config.get('database'),
                schema=self.connection_config.get('schema')
            )
            logger.info("Connected to Snowflake")
        except ImportError:
            raise ImportError("snowflake-connector-python package is required for Snowflake connections")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            df = cursor.fetch_pandas_all()
            cursor.close()
            return df
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def validate_readonly_query(self, query: str) -> bool:
        query_upper = query.strip().upper()
        readonly_keywords = ['SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC']
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'MERGE']
        
        starts_with_readonly = any(query_upper.startswith(keyword) for keyword in readonly_keywords)
        contains_forbidden = any(keyword in query_upper for keyword in forbidden_keywords)
        
        return starts_with_readonly and not contains_forbidden

class OracleConnector(DatabaseConnector):
    """Oracle database connector"""
    
    def connect(self):
        try:
            import cx_Oracle
            
            dsn = cx_Oracle.makedsn(
                self.connection_config['host'],
                self.connection_config['port'],
                service_name=self.connection_config['service_name']
            )
            
            self.connection = cx_Oracle.connect(
                user=self.connection_config['user'],
                password=self.connection_config['password'],
                dsn=dsn
            )
            logger.info("Connected to Oracle")
        except ImportError:
            raise ImportError("cx_Oracle package is required for Oracle connections")
        except Exception as e:
            logger.error(f"Failed to connect to Oracle: {e}")
            raise
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Oracle")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        
        try:
            df = pd.read_sql(query, self.connection, params=params or {})
            return df
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def validate_readonly_query(self, query: str) -> bool:
        query_upper = query.strip().upper()
        readonly_keywords = ['SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC']
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'MERGE']
        
        starts_with_readonly = any(query_upper.startswith(keyword) for keyword in readonly_keywords)
        contains_forbidden = any(keyword in query_upper for keyword in forbidden_keywords)
        
        return starts_with_readonly and not contains_forbidden

class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector"""
    
    def connect(self):
        try:
            import psycopg2
            
            self.connection = psycopg2.connect(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                database=self.connection_config['database'],
                user=self.connection_config['user'],
                password=self.connection_config['password']
            )
            logger.info("Connected to PostgreSQL")
        except ImportError:
            raise ImportError("psycopg2 package is required for PostgreSQL connections")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        if not self.validate_readonly_query(query):
            raise ValueError("Only SELECT queries are allowed")
        
        try:
            df = pd.read_sql(query, self.connection, params=params or {})
            return df
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def validate_readonly_query(self, query: str) -> bool:
        query_upper = query.strip().upper()
        readonly_keywords = ['SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC']
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'MERGE']
        
        starts_with_readonly = any(query_upper.startswith(keyword) for keyword in readonly_keywords)
        contains_forbidden = any(keyword in query_upper for keyword in forbidden_keywords)
        
        return starts_with_readonly and not contains_forbidden

class DatabaseManager:
    """Manages multiple database connections from the async MCP service layer.

    All connector methods are blocking and are executed on worker threads using
    ``asyncio.to_thread``. This keeps the event loop responsive while running
    DB driver calls.
    """
    
    def __init__(self):
        self.connectors: Dict[str, DatabaseConnector] = {}
        self.operation_timeout_seconds = 30

    async def _run_blocking(self, operation, *args, timeout: Optional[int] = None):
        """Run a blocking connector operation in a worker thread.

        Cancellation and timeout are propagated to the caller. Note that Python
        threads cannot be forcefully interrupted; cancellation/timeout only
        stops awaiting the result while the DB driver call may still complete in
        the background.
        """
        timeout_seconds = timeout if timeout is not None else self.operation_timeout_seconds

        try:
            return await asyncio.wait_for(asyncio.to_thread(operation, *args), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            operation_name = getattr(operation, "__name__", str(operation))
            raise TimeoutError(f"Operation '{operation_name}' timed out after {timeout_seconds} seconds") from exc
        except asyncio.CancelledError:
            logger.warning("Blocking database operation cancelled")
            raise
    
    @staticmethod
    def _resolve_config_with_env(config: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Resolve configuration values from environment variables if not provided"""
        resolved_config = config.copy()
        
        # Common environment variable mappings
        env_mappings = {
            'user': f'{db_type.upper()}_USER',
            'password': f'{db_type.upper()}_PASSWORD',
            'host': f'{db_type.upper()}_HOST',
            'port': f'{db_type.upper()}_PORT',
        }
        
        # Database-specific mappings
        if db_type.lower() == 'snowflake':
            env_mappings.update({
                'account': 'SNOWFLAKE_ACCOUNT',
                'warehouse': 'SNOWFLAKE_WAREHOUSE',
                'database': 'SNOWFLAKE_DATABASE',
                'schema': 'SNOWFLAKE_SCHEMA'
            })
        elif db_type.lower() == 'oracle':
            env_mappings.update({
                'service_name': 'ORACLE_SERVICE_NAME'
            })
        elif db_type.lower() == 'postgresql':
            env_mappings.update({
                'database': 'POSTGRESQL_DATABASE'
            })
        
        # Resolve values from environment variables
        for config_key, env_var in env_mappings.items():
            if config_key not in resolved_config or resolved_config[config_key] is None:
                env_value = os.getenv(env_var)
                if env_value:
                    # Convert port to integer if it's the port field
                    if config_key == 'port':
                        try:
                            resolved_config[config_key] = int(env_value)
                        except ValueError:
                            raise ValueError(f"Invalid port value in {env_var}: {env_value}")
                    else:
                        resolved_config[config_key] = env_value
        
        return resolved_config
    
    async def add_connection(self, name: str, db_type: str, config: Dict[str, Any]):
        """Add a new database connection with environment variable support"""
        # Resolve configuration from environment variables
        resolved_config = self._resolve_config_with_env(config, db_type)
        
        # Validate required fields are present
        required_fields = {
            'snowflake': ['user', 'password', 'account'],
            'oracle': ['user', 'password', 'host', 'port', 'service_name'],
            'postgresql': ['user', 'password', 'host', 'port', 'database']
        }
        
        db_type_lower = db_type.lower()
        if db_type_lower in required_fields:
            missing_fields = [field for field in required_fields[db_type_lower] 
                            if field not in resolved_config or resolved_config[field] is None]
            if missing_fields:
                raise ValueError(f"Missing required configuration for {db_type}: {missing_fields}")
        
        if db_type_lower == 'snowflake':
            connector = SnowflakeConnector(resolved_config)
        elif db_type_lower == 'oracle':
            connector = OracleConnector(resolved_config)
        elif db_type_lower == 'postgresql':
            connector = PostgreSQLConnector(resolved_config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        await self._run_blocking(connector.connect)
        self.connectors[name] = connector
    
    async def remove_connection(self, name: str):
        """Remove a database connection"""
        if name in self.connectors:
            await self._run_blocking(self.connectors[name].disconnect)
            del self.connectors[name]
    
    async def execute_query(self, connection_name: str, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute query on specified connection via a worker thread."""
        if connection_name not in self.connectors:
            raise ValueError(f"Connection '{connection_name}' not found")
        
        connector = self.connectors[connection_name]
        return await self._run_blocking(connector.execute_query, query, params)

    async def shutdown(self):
        """Close all active connections during server shutdown."""
        connection_names = list(self.connectors.keys())
        for name in connection_names:
            try:
                await self.remove_connection(name)
            except Exception as exc:
                logger.error("Failed to close connection '%s' during shutdown: %s", name, exc)

class DataComparator:
    """Utilities for comparing data between databases"""
    
    @staticmethod
    def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, name1: str = "DataFrame1", name2: str = "DataFrame2") -> Dict[str, Any]:
        """Compare two DataFrames and return comparison results"""
        comparison = {
            "row_count_match": len(df1) == len(df2),
            "row_count_df1": len(df1),
            "row_count_df2": len(df2),
            "column_count_match": len(df1.columns) == len(df2.columns),
            "column_count_df1": len(df1.columns),
            "column_count_df2": len(df2.columns),
            "column_names_match": list(df1.columns) == list(df2.columns),
            "column_names_df1": list(df1.columns),
            "column_names_df2": list(df2.columns),
            "data_types_match": True,
            "data_types_differences": [],
            "data_content_match": False,
            "content_differences": []
        }
        
        # Compare data types
        if comparison["column_names_match"]:
            for col in df1.columns:
                if col in df2.columns:
                    if df1[col].dtype != df2[col].dtype:
                        comparison["data_types_match"] = False
                        comparison["data_types_differences"].append({
                            "column": col,
                            f"{name1}_dtype": str(df1[col].dtype),
                            f"{name2}_dtype": str(df2[col].dtype)
                        })
        
        # Compare content if structure matches
        if (comparison["row_count_match"] and 
            comparison["column_names_match"] and 
            comparison["data_types_match"]):
            try:
                comparison["data_content_match"] = df1.equals(df2)
                if not comparison["data_content_match"]:
                    # Find differences
                    for col in df1.columns:
                        if not df1[col].equals(df2[col]):
                            comparison["content_differences"].append(col)
            except Exception as e:
                comparison["content_differences"] = [f"Error comparing content: {str(e)}"]
        
        return comparison
    
    @staticmethod
    def detect_schema_differences(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, Any]:
        """Detect differences in column names and data types"""
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        
        return {
            "columns_only_in_df1": list(cols1 - cols2),
            "columns_only_in_df2": list(cols2 - cols1),
            "common_columns": list(cols1.intersection(cols2)),
            "dtype_differences": [
                {
                    "column": col,
                    "df1_dtype": str(df1[col].dtype),
                    "df2_dtype": str(df2[col].dtype)
                }
                for col in cols1.intersection(cols2)
                if df1[col].dtype != df2[col].dtype
            ]
        }

class TestGenerator:
    """Generate pytest test scripts for data comparison"""
    
    @staticmethod
    def generate_comparison_test(
        connection1: str, query1: str,
        connection2: str, query2: str,
        test_name: str = "test_data_comparison"
    ) -> str:
        """Generate a pytest test script for comparing query results"""
        
        test_code = f'''import pytest
import pandas as pd
from server import DatabaseManager, DataComparator

@pytest.mark.asyncio
async def {test_name}():
    """Compare data between {connection1} and {connection2}"""
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Execute queries
    query1 = """{query1}"""
    query2 = """{query2}"""
    
    df1 = await db_manager.execute_query("{connection1}", query1)
    df2 = await db_manager.execute_query("{connection2}", query2)
    
    # Compare results
    comparison = DataComparator.compare_dataframes(df1, df2, "{connection1}", "{connection2}")
    
    # Assertions
    assert comparison["row_count_match"], f"Row count mismatch: {{comparison['row_count_df1']}} vs {{comparison['row_count_df2']}}"
    assert comparison["column_names_match"], f"Column names mismatch: {{comparison['column_names_df1']}} vs {{comparison['column_names_df2']}}"
    assert comparison["data_types_match"], f"Data types mismatch: {{comparison['data_types_differences']}}"
    assert comparison["data_content_match"], f"Data content mismatch in columns: {{comparison['content_differences']}}"
    
    print(f"✓ Data comparison passed for {connection1} vs {connection2}")

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
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Connection name"},
                    "db_type": {"type": "string", "enum": ["snowflake", "oracle", "postgresql"], "description": "Database type"},
                    "config": {"type": "object", "description": "Database connection configuration"}
                },
                "required": ["name", "db_type", "config"]
            }
        ),
        Tool(
            name="execute_query",
            description="Execute a read-only query on a database connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_name": {"type": "string", "description": "Name of the database connection"},
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "limit": {"type": "integer", "description": "Optional row limit", "default": 50}
                },
                "required": ["connection_name", "query"]
            }
        ),
        Tool(
            name="compare_query_results",
            description="Compare results from two database queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string", "description": "First database connection name"},
                    "query1": {"type": "string", "description": "First query"},
                    "connection2": {"type": "string", "description": "Second database connection name"},
                    "query2": {"type": "string", "description": "Second query"}
                },
                "required": ["connection1", "query1", "connection2", "query2"]
            }
        ),
        Tool(
            name="detect_schema_differences",
            description="Detect differences in column names and data types between two query results",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string", "description": "First database connection name"},
                    "query1": {"type": "string", "description": "First query"},
                    "connection2": {"type": "string", "description": "Second database connection name"},
                    "query2": {"type": "string", "description": "Second query"}
                },
                "required": ["connection1", "query1", "connection2", "query2"]
            }
        ),
        Tool(
            name="generate_test_script",
            description="Generate a pytest test script for comparing query results",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection1": {"type": "string", "description": "First database connection name"},
                    "query1": {"type": "string", "description": "First query"},
                    "connection2": {"type": "string", "description": "Second database connection name"},
                    "query2": {"type": "string", "description": "Second query"},
                    "test_name": {"type": "string", "description": "Name for the test function", "default": "test_data_comparison"}
                },
                "required": ["connection1", "query1", "connection2", "query2"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls using thread-offloaded connector operations."""
    
    try:
        if name == "add_database_connection":
            connection_name = arguments["name"]
            db_type = arguments["db_type"]
            config = arguments["config"]
            
            await db_manager.add_connection(connection_name, db_type, config)
            return [TextContent(type="text", text=f"Successfully added {db_type} connection '{connection_name}'")]
        
        elif name == "execute_query":
            connection_name = arguments["connection_name"]
            query = arguments["query"]
            limit = arguments.get("limit", 50)
            
            # Add database-specific limit clause if not present
            if limit and not any(keyword in query.upper() for keyword in ["LIMIT", "ROWNUM", "TOP"]):
                # Get the connector to determine database type
                if connection_name in db_manager.connectors:
                    connector = db_manager.connectors[connection_name]
                    
                    # Apply database-specific limit syntax
                    if isinstance(connector, OracleConnector):
                        # Oracle uses ROWNUM - add to WHERE clause or create one
                        query_stripped = query.rstrip(';').strip()
                        if " WHERE " in query_stripped.upper():
                            query = f"{query_stripped} AND ROWNUM <= {limit}"
                        else:
                            query = f"{query_stripped} WHERE ROWNUM <= {limit}"
                    elif isinstance(connector, (SnowflakeConnector, PostgreSQLConnector)):
                        # Snowflake and PostgreSQL use LIMIT
                        query = f"{query.rstrip(';')} LIMIT {limit}"
            
            df = await db_manager.execute_query(connection_name, query)
            
            result = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_data": df.head(10).to_dict('records') if len(df) > 0 else []
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "compare_query_results":
            connection1 = arguments["connection1"]
            query1 = arguments["query1"]
            connection2 = arguments["connection2"]
            query2 = arguments["query2"]
            
            df1 = await db_manager.execute_query(connection1, query1)
            df2 = await db_manager.execute_query(connection2, query2)
            
            comparison = DataComparator.compare_dataframes(df1, df2, connection1, connection2)
            
            return [TextContent(type="text", text=json.dumps(comparison, indent=2))]
        
        elif name == "detect_schema_differences":
            connection1 = arguments["connection1"]
            query1 = arguments["query1"]
            connection2 = arguments["connection2"]
            query2 = arguments["query2"]
            
            df1 = await db_manager.execute_query(connection1, query1)
            df2 = await db_manager.execute_query(connection2, query2)
            
            differences = DataComparator.detect_schema_differences(df1, df2)
            
            return [TextContent(type="text", text=json.dumps(differences, indent=2))]
        
        elif name == "generate_test_script":
            connection1 = arguments["connection1"]
            query1 = arguments["query1"]
            connection2 = arguments["connection2"]
            query2 = arguments["query2"]
            test_name = arguments.get("test_name", "test_data_comparison")
            
            test_code = TestGenerator.generate_comparison_test(
                connection1, query1, connection2, query2, test_name
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
        try:
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
        finally:
            await db_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
