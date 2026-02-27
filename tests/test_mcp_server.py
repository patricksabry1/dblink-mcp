#!/usr/bin/env python3
"""
Comprehensive test suite for DBLink MCP Server functionality
"""
import pytest
import asyncio
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
import json
from server import (
    DatabaseManager, 
    DataComparator, 
    TestGenerator,
    PostgreSQLConnector,
    OracleConnector,
    SnowflakeConnector
)

class TestDatabaseConnectors:
    """Test database connector implementations"""
    
    def test_postgresql_connector_init(self):
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        connector = PostgreSQLConnector(config)
        assert connector.connection_config == config
        assert connector.connection is None
    
    def test_oracle_connector_init(self):
        config = {
            'host': 'localhost',
            'port': 1521,
            'service_name': 'TESTDB',
            'user': 'testuser',
            'password': 'testpass'
        }
        connector = OracleConnector(config)
        assert connector.connection_config == config
        assert connector.connection is None
    
    @pytest.mark.parametrize("query,expected", [
        ("SELECT * FROM table", True),
        ("select id, name from users", True),
        ("WITH cte AS (SELECT * FROM table) SELECT * FROM cte", True),
        ("SHOW TABLES", True),
        ("DESCRIBE table", True),
        ("INSERT INTO table VALUES (1, 'test')", False),
        ("UPDATE table SET name = 'test'", False),
        ("DELETE FROM table", False),
        ("DROP TABLE table", False),
        ("CREATE TABLE test (id INT)", False),
        ("ALTER TABLE test ADD COLUMN name VARCHAR(50)", False),
        ("TRUNCATE TABLE test", False),
        ("MERGE INTO target USING source ON condition", False),
    ])
    def test_query_validation(self, query, expected):
        connector = PostgreSQLConnector({})
        assert connector.validate_readonly_query(query) == expected

class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    @pytest.fixture
    def db_manager(self):
        return DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_add_postgresql_connection(self, db_manager):
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        
        with patch.object(PostgreSQLConnector, 'connect'):
            await db_manager.add_connection('test_pg', 'postgresql', config)
            assert 'test_pg' in db_manager.connectors
            assert isinstance(db_manager.connectors['test_pg'], PostgreSQLConnector)
    
    @pytest.mark.asyncio
    async def test_add_oracle_connection(self, db_manager):
        config = {
            'host': 'localhost',
            'port': 1521,
            'service_name': 'TESTDB',
            'user': 'testuser',
            'password': 'testpass'
        }
        
        with patch.object(OracleConnector, 'connect'):
            await db_manager.add_connection('test_oracle', 'oracle', config)
            assert 'test_oracle' in db_manager.connectors
            assert isinstance(db_manager.connectors['test_oracle'], OracleConnector)
    
    @pytest.mark.asyncio
    async def test_unsupported_database_type(self, db_manager):
        with pytest.raises(ValueError, match="Unsupported database type: mysql"):
            await db_manager.add_connection('test', 'mysql', {})
    
    @pytest.mark.asyncio
    async def test_remove_connection(self, db_manager):
        config = {'host': 'localhost', 'port': 5432, 'database': 'testdb', 'user': 'test', 'password': 'test'}
        
        with patch.object(PostgreSQLConnector, 'connect'):
            with patch.object(PostgreSQLConnector, 'disconnect') as mock_disconnect:
                await db_manager.add_connection('test_pg', 'postgresql', config)
                await db_manager.remove_connection('test_pg')
                
                mock_disconnect.assert_called_once()
                assert 'test_pg' not in db_manager.connectors
    
    @pytest.mark.asyncio
    async def test_execute_query_unknown_connection(self, db_manager):
        with pytest.raises(ValueError, match="Connection 'unknown' not found"):
            await db_manager.execute_query('unknown', 'SELECT 1')


    @pytest.mark.asyncio
    async def test_execute_query_runs_in_thread_wrapper(self, db_manager):
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }

        expected_df = pd.DataFrame({'id': [1]})

        with patch.object(PostgreSQLConnector, 'connect'):
            await db_manager.add_connection('test_pg', 'postgresql', config)

        with patch.object(db_manager, '_run_blocking', new_callable=AsyncMock, return_value=expected_df) as mock_run_blocking:
            result = await db_manager.execute_query('test_pg', 'SELECT 1')

        assert result.equals(expected_df)
        mock_run_blocking.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_all_connections(self, db_manager):
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }

        with patch.object(PostgreSQLConnector, 'connect'):
            await db_manager.add_connection('pg1', 'postgresql', config)
            await db_manager.add_connection('pg2', 'postgresql', config)

        with patch.object(db_manager, 'remove_connection', new_callable=AsyncMock) as mock_remove:
            await db_manager.shutdown()

        assert mock_remove.await_count == 2

class TestDataComparator:
    """Test data comparison functionality"""
    
    def test_compare_identical_dataframes(self):
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'salary': [50000.0, 60000.0, 70000.0]
        })
        df2 = df1.copy()
        
        result = DataComparator.compare_dataframes(df1, df2)
        
        assert result['row_count_match'] is True
        assert result['column_names_match'] is True
        assert result['data_types_match'] is True
        assert result['data_content_match'] is True
        assert len(result['data_types_differences']) == 0
        assert len(result['content_differences']) == 0
    
    def test_compare_different_row_counts(self):
        df1 = pd.DataFrame({'id': [1, 2, 3], 'name': ['A', 'B', 'C']})
        df2 = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        
        result = DataComparator.compare_dataframes(df1, df2)
        
        assert result['row_count_match'] is False
        assert result['row_count_df1'] == 3
        assert result['row_count_df2'] == 2
    
    def test_compare_different_column_names(self):
        df1 = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        df2 = pd.DataFrame({'id': [1, 2], 'full_name': ['A', 'B']})
        
        result = DataComparator.compare_dataframes(df1, df2)
        
        assert result['column_names_match'] is False
        assert result['column_names_df1'] == ['id', 'name']
        assert result['column_names_df2'] == ['id', 'full_name']
    
    def test_compare_different_data_types(self):
        df1 = pd.DataFrame({'id': [1, 2], 'value': [1.0, 2.0]})
        df2 = pd.DataFrame({'id': [1, 2], 'value': [1, 2]})
        
        result = DataComparator.compare_dataframes(df1, df2)
        
        assert result['data_types_match'] is False
        assert len(result['data_types_differences']) == 1
        assert result['data_types_differences'][0]['column'] == 'value'
    
    def test_detect_schema_differences(self):
        df1 = pd.DataFrame({
            'id': [1, 2], 
            'name': ['A', 'B'], 
            'salary': [50000.0, 60000.0]
        })
        df2 = pd.DataFrame({
            'id': [1, 2], 
            'full_name': ['A', 'B'], 
            'salary': [50000, 60000]  # Different dtype
        })
        
        result = DataComparator.detect_schema_differences(df1, df2)
        
        assert 'name' in result['columns_only_in_df1']
        assert 'full_name' in result['columns_only_in_df2']
        assert 'id' in result['common_columns']
        assert 'salary' in result['common_columns']
        assert len(result['dtype_differences']) == 1
        assert result['dtype_differences'][0]['column'] == 'salary'

class TestTestGenerator:
    """Test pytest test script generation"""
    
    def test_generate_comparison_test(self):
        test_code = TestGenerator.generate_comparison_test(
            'db1', 'SELECT * FROM table1',
            'db2', 'SELECT * FROM table2',
            'test_data_sync'
        )
        
        assert 'def test_data_sync():' in test_code
        assert 'SELECT * FROM table1' in test_code
        assert 'SELECT * FROM table2' in test_code
        assert 'db1' in test_code
        assert 'db2' in test_code
        assert 'assert comparison["row_count_match"]' in test_code
        assert 'assert comparison["column_names_match"]' in test_code
        assert 'assert comparison["data_types_match"]' in test_code
        assert 'assert comparison["data_content_match"]' in test_code

class TestIntegrationScenarios:
    """Integration tests for common MCP usage scenarios"""
    
    @pytest.fixture
    def sample_employee_data(self):
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson'],
            'department': ['Engineering', 'Marketing', 'Engineering', 'HR', 'Finance'],
            'salary': [75000.00, 65000.00, 80000.00, 55000.00, 70000.00],
            'hire_date': pd.to_datetime(['2020-01-15', '2020-03-20', '2019-08-10', '2021-05-12', '2020-11-08']),
            'is_active': [True, True, True, False, True]
        })
    
    @pytest.fixture
    def sample_department_data(self):
        return pd.DataFrame({
            'id': [1, 2, 3, 4],
            'name': ['Engineering', 'Marketing', 'HR', 'Finance'],
            'budget': [500000.00, 200000.00, 150000.00, 300000.00],
            'location': ['San Francisco', 'New York', 'Chicago', 'Boston']
        })
    
    def test_data_comparison_workflow(self, sample_employee_data):
        """Test the complete data comparison workflow"""
        # Simulate slight differences in data
        df_oracle = sample_employee_data.copy()
        df_postgres = sample_employee_data.copy()
        
        # Make PostgreSQL version have boolean instead of integer for is_active
        df_postgres['is_active'] = df_postgres['is_active'].astype(bool)
        df_oracle['is_active'] = df_oracle['is_active'].astype(int)
        
        # Compare the data
        comparison = DataComparator.compare_dataframes(df_oracle, df_postgres, "Oracle", "PostgreSQL")
        
        # Should detect data type differences
        assert comparison['row_count_match'] is True
        assert comparison['column_names_match'] is True
        assert comparison['data_types_match'] is False
        assert len(comparison['data_types_differences']) == 1
        assert comparison['data_types_differences'][0]['column'] == 'is_active'
    
    def test_schema_analysis_workflow(self, sample_employee_data, sample_department_data):
        """Test schema difference detection"""
        differences = DataComparator.detect_schema_differences(sample_employee_data, sample_department_data)
        
        assert len(differences['columns_only_in_df1']) > 0
        assert len(differences['columns_only_in_df2']) > 0
        assert 'id' in differences['common_columns']
        assert 'name' in differences['common_columns']
    
    def test_test_generation_workflow(self):
        """Test the test script generation workflow"""
        test_script = TestGenerator.generate_comparison_test(
            'oracle_prod', 'SELECT * FROM testschema.employees LIMIT 50',
            'postgres_test', 'SELECT * FROM testschema.employees LIMIT 50',
            'test_employee_data_migration'
        )
        
        # Verify the generated test has all required components
        assert 'import pytest' in test_script
        assert 'import pandas as pd' in test_script
        assert 'from server import DatabaseManager, DataComparator' in test_script
        assert '@pytest.mark.asyncio' in test_script
        assert 'async def test_employee_data_migration():' in test_script
        assert 'testschema.employees' in test_script
        
        # Verify assertions are present
        required_assertions = [
            'assert comparison["row_count_match"]',
            'assert comparison["column_names_match"]',
            'assert comparison["data_types_match"]',
            'assert comparison["data_content_match"]'
        ]
        
        for assertion in required_assertions:
            assert assertion in test_script

if __name__ == "__main__":
    pytest.main([__file__, "-v"])