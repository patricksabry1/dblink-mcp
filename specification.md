# MCP for automating cross database querying and testing using Python

# Goals

1. Provide a way for LLM agent to connect to multiple different remote databases. Currently only need support for Snowflake and Oracle, but design should leverage a strategy pattern to plug and play different DB connectors.
2. MCP should restrict access to read-only querying within specified schemas.
3. MCP should help facilitate data comparison between two queries from two different databases. This should be done by loading the query data from each database into Pandas DataFrame.
4. The assumption is the table names and column definitions should be the same across the databases. If they aren't there should be utilities to detect differences in column names and data types.

A common use case flow:

1. Fetch first 50 rows from <schema>.TABLE1 in Snowflake
2. Fetch first 50 rows from <schema>.TABLE1 in Oracle
3. Write an integration test script in python using pytest that compares the results for equality - same count, same column names, same data types, same floating point precisions etc.
4. Execute test to ensure assertions are truthy and tests pass.
