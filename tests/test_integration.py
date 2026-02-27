#!/usr/bin/env python3
"""
Integration tests for DBLink MCP Server with real database connections
These tests require the Docker Compose environment to be running
"""
import pytest
import asyncio
import os
import pandas as pd
from dblink_mcp.server import DatabaseManager, DataComparator, TestGenerator

# Test configuration
ORACLE_CONFIG = {
    'host': 'localhost',
    'port': 1521,
    'service_name': 'TESTDB',
    'user': 'testuser',
    'password': 'testpass'
}

POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'testdb',
    'user': 'testuser',
    'password': 'testpass'
}

class TestDatabaseIntegration:
    """Integration tests with real database connections"""
    
    @pytest.fixture(scope="class")
    async def db_manager(self):
        """Set up database connections for the test class"""
        manager = DatabaseManager()
        
        # Skip tests if databases are not available
        try:
            await manager.add_connection('oracle_test', 'oracle', ORACLE_CONFIG)
            await manager.add_connection('postgres_test', 'postgresql', POSTGRES_CONFIG)
            yield manager
        except Exception as e:
            pytest.skip(f"Database connections not available: {e}")
        finally:
            # Clean up connections
            if 'oracle_test' in manager.connectors:
                await manager.remove_connection('oracle_test')
            if 'postgres_test' in manager.connectors:
                await manager.remove_connection('postgres_test')
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_connections(self, db_manager):
        """Test that database connections can be established"""
        assert 'oracle_test' in db_manager.connectors
        assert 'postgres_test' in db_manager.connectors
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_execution(self, db_manager):
        """Test query execution on both databases"""
        oracle_query = "SELECT COUNT(*) as count FROM testschema.employees"
        postgres_query = "SELECT COUNT(*) as count FROM testschema.employees"
        
        oracle_result = await db_manager.execute_query('oracle_test', oracle_query)
        postgres_result = await db_manager.execute_query('postgres_test', postgres_query)
        
        assert len(oracle_result) == 1
        assert len(postgres_result) == 1
        assert 'count' in oracle_result.columns
        assert 'count' in postgres_result.columns
        assert oracle_result.iloc[0]['count'] == postgres_result.iloc[0]['count']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_comparison_end_to_end(self, db_manager):
        """Test complete data comparison workflow"""
        oracle_query = "SELECT id, name, department, salary FROM testschema.employees ORDER BY id"
        postgres_query = "SELECT id, name, department, salary FROM testschema.employees ORDER BY id"
        
        oracle_data = await db_manager.execute_query('oracle_test', oracle_query)
        postgres_data = await db_manager.execute_query('postgres_test', postgres_query)
        
        comparison = DataComparator.compare_dataframes(oracle_data, postgres_data, "Oracle", "PostgreSQL")
        
        # Basic structure should match
        assert comparison['row_count_match'] is True
        assert comparison['column_names_match'] is True
        assert comparison['row_count_df1'] == 5  # Expected number of test records
        assert comparison['row_count_df2'] == 5
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_schema_differences_detection(self, db_manager):
        """Test detection of schema differences between databases"""
        # Query with boolean/integer difference
        oracle_query = "SELECT id, name, is_active FROM testschema.employees ORDER BY id"
        postgres_query = "SELECT id, name, is_active FROM testschema.employees ORDER BY id"
        
        oracle_data = await db_manager.execute_query('oracle_test', oracle_query)
        postgres_data = await db_manager.execute_query('postgres_test', postgres_query)
        
        differences = DataComparator.detect_schema_differences(oracle_data, postgres_data)
        
        # Should have common columns
        assert 'id' in differences['common_columns']
        assert 'name' in differences['common_columns']
        assert 'is_active' in differences['common_columns']
        
        # May have data type differences due to Oracle NUMBER vs PostgreSQL BOOLEAN
        # This is expected and demonstrates the utility of the tool
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_readonly_query_enforcement(self, db_manager):
        """Test that write operations are blocked"""
        malicious_queries = [
            "INSERT INTO testschema.employees (name) VALUES ('hacker')",
            "UPDATE testschema.employees SET salary = 999999",
            "DELETE FROM testschema.employees",
            "DROP TABLE testschema.employees",
            "CREATE TABLE malicious (id INT)"
        ]
        
        for query in malicious_queries:
            with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
                await db_manager.execute_query('oracle_test', query)
            
            with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
                await db_manager.execute_query('postgres_test', query)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_test_script_generation_with_real_data(self, db_manager):
        """Test generating and validating test scripts with real data"""
        oracle_query = "SELECT * FROM testschema.departments ORDER BY id"
        postgres_query = "SELECT * FROM testschema.departments ORDER BY id"
        
        test_script = TestGenerator.generate_comparison_test(
            'oracle_test', oracle_query,
            'postgres_test', postgres_query,
            'test_departments_sync'
        )
        
        # Verify the script can be executed (syntax check)
        exec(compile(test_script, '<generated_test>', 'exec'))
        
        # Verify test content
        assert 'testschema.departments' in test_script
        assert 'test_departments_sync' in test_script

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failures"""
        bad_config = {
            'host': 'nonexistent-host',
            'port': 9999,
            'database': 'nonexistent',
            'user': 'fake',
            'password': 'fake'
        }
        
        manager = DatabaseManager()
        
        with pytest.raises(Exception):  # Should raise connection error
            await manager.add_connection('bad_connection', 'postgresql', bad_config)
    
    @pytest.mark.asyncio
    async def test_invalid_query_syntax(self):
        """Test handling of invalid SQL syntax"""
        manager = DatabaseManager()
        
        # Mock a connection to avoid actual database dependency
        from unittest.mock import Mock, AsyncMock
        mock_connector = Mock()
        mock_connector.execute_query = AsyncMock(side_effect=Exception("SQL syntax error"))
        mock_connector.validate_readonly_query = Mock(return_value=True)
        
        manager.connectors['test'] = mock_connector
        
        with pytest.raises(Exception, match="SQL syntax error"):
            await manager.execute_query('test', 'SELECT * FROM nonexistent_syntax error')

class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_queries(self):
        """Test handling multiple concurrent queries"""
        manager = DatabaseManager()
        
        # Mock multiple connections
        from unittest.mock import Mock, AsyncMock
        import pandas as pd
        
        for i in range(5):
            mock_connector = Mock()
            mock_connector.execute_query = AsyncMock(return_value=pd.DataFrame({'id': [1, 2, 3]}))
            mock_connector.validate_readonly_query = Mock(return_value=True)
            manager.connectors[f'conn_{i}'] = mock_connector
        
        # Execute queries concurrently
        tasks = []
        for i in range(5):
            tasks.append(manager.execute_query(f'conn_{i}', 'SELECT * FROM test'))
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for result in results:
            assert len(result) == 3  # 3 rows as mocked

if __name__ == "__main__":
    # Run with: pytest tests/test_integration.py -v -m integration
    # Or: pytest tests/test_integration.py -v -m "not integration" (skip integration tests)
    pytest.main([__file__, "-v"])