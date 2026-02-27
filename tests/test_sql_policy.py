import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from dblink_mcp.config.models import QueryPolicyConfig
from dblink_mcp.security.sql_policy import SQLPolicyError, evaluate_sql_policy


def test_allows_select_by_default():
    evaluate_sql_policy("SELECT * FROM users")


def test_denies_multi_statement():
    with pytest.raises(SQLPolicyError, match="Multi-statement"):
        evaluate_sql_policy("SELECT 1; SELECT 2")


def test_schema_allowlist_blocks_disallowed_schema():
    policy = QueryPolicyConfig(allowed_schemas={"public"})
    evaluate_sql_policy("SELECT * FROM public.users", policy)

    with pytest.raises(SQLPolicyError, match="disallowed schemas"):
        evaluate_sql_policy("SELECT * FROM admin.users", policy)


def test_table_allowlist_blocks_disallowed_table():
    policy = QueryPolicyConfig(allowed_tables={"users"})
    evaluate_sql_policy("SELECT * FROM users", policy)

    with pytest.raises(SQLPolicyError, match="disallowed tables"):
        evaluate_sql_policy("SELECT * FROM payments", policy)


def test_statement_policy():
    with pytest.raises(SQLPolicyError, match="not allowed"):
        evaluate_sql_policy("SHOW TABLES", QueryPolicyConfig(allowed_statement_types={"select"}))
