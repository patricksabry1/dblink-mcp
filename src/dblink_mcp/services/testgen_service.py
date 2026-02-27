class TestGenerator:
    @staticmethod
    def generate_comparison_test(
        connection1: str,
        query1: str,
        connection2: str,
        query2: str,
        test_name: str = "test_data_comparison",
    ) -> str:
        return f'''import pytest
from dblink_mcp.services.query_service import DatabaseManager
from dblink_mcp.services.comparison_service import DataComparator

@pytest.mark.asyncio
async def {test_name}():
    """Compare data between {connection1} and {connection2}"""
    db_manager = DatabaseManager()

    query1 = """{query1}"""
    query2 = """{query2}"""

    df1 = await db_manager.execute_query("{connection1}", query1)
    df2 = await db_manager.execute_query("{connection2}", query2)

    comparison = DataComparator.compare_dataframes(df1, df2, "{connection1}", "{connection2}")

    assert comparison["row_count_match"], f"Row count mismatch: {{comparison['row_count_df1']}} vs {{comparison['row_count_df2']}}"
    assert comparison["column_names_match"], f"Column names mismatch: {{comparison['column_names_df1']}} vs {{comparison['column_names_df2']}}"
    assert comparison["data_types_match"], f"Data types mismatch: {{comparison['data_types_differences']}}"
    assert comparison["data_content_match"], f"Data content mismatch in columns: {{comparison['content_differences']}}"
'''
