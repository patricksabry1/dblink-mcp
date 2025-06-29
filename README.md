# DBLink MCP Server

An MCP (Model Context Protocol) server for automating cross-database querying and testing. Supports connecting to multiple databases, executing read-only queries, and comparing data between different database systems.

## Features

- **Multi-database support**: Snowflake and Oracle with pluggable connector architecture
- **Read-only query validation**: Ensures only SELECT statements are executed
- **Schema-restricted access**: Limits queries to specified schemas
- **Data comparison**: Compare query results between different databases using Pandas DataFrames
- **Schema analysis**: Detect differences in column names and data types
- **Test generation**: Automatically generate pytest scripts for data validation

## Installation

```bash
pip install -e .
```

## Usage

### Running the MCP Server

```bash
python server.py
```

The server runs using stdio transport and provides the following tools:

### Available Tools

#### 1. `add_database_connection`
Add a new database connection.

**Parameters:**
- `name` (string): Connection identifier
- `db_type` (string): "snowflake" or "oracle"
- `config` (object): Database connection configuration

**Configuration with Environment Variables (Recommended):**

For security, you can store credentials in environment variables instead of passing them directly. The server will automatically use environment variables when config values are not provided.

**Snowflake config example:**
```json
{
  "account": "account_identifier",
  "warehouse": "warehouse_name",
  "database": "database_name",
  "schema": "schema_name"
}
```

Set these environment variables:
```bash
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_HOST=your_host
export SNOWFLAKE_PORT=443
```

**Oracle config example:**
```json
{
  "host": "hostname",
  "port": 1521,
  "service_name": "service_name"
}
```

Set these environment variables:
```bash
export ORACLE_USER=your_username
export ORACLE_PASSWORD=your_password
```

**PostgreSQL config example:**
```json
{
  "host": "hostname",
  "port": 5432,
  "database": "database_name"
}
```

Set these environment variables:
```bash
export POSTGRESQL_USER=your_username
export POSTGRESQL_PASSWORD=your_password
```

**Direct config (not recommended for production):**
```json
{
  "user": "username",
  "password": "password",
  "host": "hostname",
  "port": 5432,
  "database": "database_name"
}
```

#### 2. `execute_query`
Execute a read-only query on a database connection.

**Parameters:**
- `connection_name` (string): Name of the database connection
- `query` (string): SQL SELECT query
- `limit` (integer, optional): Row limit (default: 50)

#### 3. `compare_query_results`
Compare results from two database queries.

**Parameters:**
- `connection1` (string): First database connection name
- `query1` (string): First query
- `connection2` (string): Second database connection name  
- `query2` (string): Second query

#### 4. `detect_schema_differences`
Detect differences in column names and data types between query results.

**Parameters:**
- `connection1` (string): First database connection name
- `query1` (string): First query
- `connection2` (string): Second database connection name
- `query2` (string): Second query

#### 5. `generate_test_script`
Generate a pytest test script for comparing query results.

**Parameters:**
- `connection1` (string): First database connection name
- `query1` (string): First query
- `connection2` (string): Second database connection name
- `query2` (string): Second query
- `test_name` (string, optional): Test function name

## Common Workflow

1. **Add database connections:**
   ```
   Use add_database_connection for both Snowflake and Oracle
   ```

2. **Query data from each database:**
   ```
   Use execute_query to fetch first 50 rows from schema.TABLE1 in Snowflake
   Use execute_query to fetch first 50 rows from schema.TABLE1 in Oracle
   ```

3. **Compare the results:**
   ```
   Use compare_query_results to check for equality in count, columns, data types, and content
   ```

4. **Generate integration test:**
   ```
   Use generate_test_script to create a pytest script that validates the comparison
   ```

## Security Features

- **Read-only enforcement**: Only SELECT, WITH, SHOW, DESCRIBE queries allowed
- **Query validation**: Blocks INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, MERGE
- **Schema restrictions**: Connections can be limited to specific schemas
- **Parameter binding**: Supports parameterized queries to prevent injection

## Environment Variables

The server supports environment variables for secure credential management. Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### Supported Environment Variables

| Database | Variable | Description |
|----------|----------|-------------|
| **Snowflake** | `SNOWFLAKE_USER` | Username |
| | `SNOWFLAKE_PASSWORD` | Password |
| | `SNOWFLAKE_ACCOUNT` | Account identifier |
| | `SNOWFLAKE_HOST` | Host (optional) |
| | `SNOWFLAKE_PORT` | Port (optional) |
| | `SNOWFLAKE_WAREHOUSE` | Warehouse name |
| | `SNOWFLAKE_DATABASE` | Database name |
| | `SNOWFLAKE_SCHEMA` | Schema name |
| **Oracle** | `ORACLE_USER` | Username |
| | `ORACLE_PASSWORD` | Password |
| | `ORACLE_HOST` | Host |
| | `ORACLE_PORT` | Port |
| | `ORACLE_SERVICE_NAME` | Service name |
| **PostgreSQL** | `POSTGRESQL_USER` | Username |
| | `POSTGRESQL_PASSWORD` | Password |
| | `POSTGRESQL_HOST` | Host |
| | `POSTGRESQL_PORT` | Port |
| | `POSTGRESQL_DATABASE` | Database name |

## Development and Testing

### Test Environment Setup

Start the containerized test environment:

```bash
# Start databases
docker-compose up -d

# Run quick functionality test
python test_runner.py --quick-test

# Run all tests
python test_runner.py

# Run only unit tests
python test_runner.py --unit-only

# Run only integration tests (requires Docker)
python test_runner.py --integration-only

# Stop test environment
docker-compose down
```

### Test Database Credentials

For the Docker test environment, use:
```bash
export ORACLE_USER=testuser
export ORACLE_PASSWORD=testpass
export POSTGRESQL_USER=testuser
export POSTGRESQL_PASSWORD=testpass
```

### Best Practices for Testing

1. **Unit Tests**: Test individual components without external dependencies
2. **Integration Tests**: Test with real database connections using Docker
3. **Environment Isolation**: Use environment variables for all credentials
4. **Data Validation**: Always compare schemas and data types between databases
5. **Security Testing**: Verify read-only query enforcement

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol framework
- `pandas>=2.0.0` - Data manipulation and analysis
- `snowflake-connector-python>=3.0.0` - Snowflake database connector
- `cx_Oracle>=8.0.0` - Oracle database connector
- `psycopg2-binary>=2.9.0` - PostgreSQL database connector
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
