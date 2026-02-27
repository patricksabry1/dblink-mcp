from dblink_mcp.providers.postgres import PostgreSQLConnector


class RedshiftConnector(PostgreSQLConnector):
    """Redshift connector reusing PostgreSQL wire compatibility."""
