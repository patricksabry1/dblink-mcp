from typing import Iterable, Optional, Set

from sqlglot import exp, parse

from dblink_mcp.config.models import QueryPolicyConfig


ALLOWED_STATEMENT_EXPRESSIONS = {
    "select": exp.Select,
    "union": exp.Union,
    "with": exp.With,
}


class SQLPolicyError(ValueError):
    pass


def _normalized_set(values: Optional[Iterable[str]]) -> Optional[Set[str]]:
    if values is None:
        return None
    return {v.lower() for v in values}


def _extract_tables(statement: exp.Expression) -> Set[str]:
    return {
        table.name.lower()
        for table in statement.find_all(exp.Table)
        if table.name
    }


def _extract_schemas(statement: exp.Expression) -> Set[str]:
    schemas = set()
    for table in statement.find_all(exp.Table):
        if table.db:
            schemas.add(str(table.db).lower())
    return schemas


def evaluate_sql_policy(query: str, policy: Optional[QueryPolicyConfig] = None) -> None:
    effective_policy = policy or QueryPolicyConfig()
    statements = parse(query)
    if len(statements) != 1:
        raise SQLPolicyError("Multi-statement SQL payloads are not allowed")

    statement = statements[0]
    allowed_types = _normalized_set(effective_policy.allowed_statement_types) or {"select"}

    allowed_exp_classes = tuple(
        ALLOWED_STATEMENT_EXPRESSIONS[t] for t in allowed_types if t in ALLOWED_STATEMENT_EXPRESSIONS
    )
    if not allowed_exp_classes:
        raise SQLPolicyError("No valid statement types configured in policy")

    if not isinstance(statement, allowed_exp_classes):
        raise SQLPolicyError(
            f"Statement type '{statement.key}' is not allowed. Allowed types: {sorted(allowed_types)}"
        )

    allowed_schemas = _normalized_set(effective_policy.allowed_schemas)
    if allowed_schemas is not None:
        query_schemas = _extract_schemas(statement)
        disallowed = query_schemas - allowed_schemas
        if disallowed:
            raise SQLPolicyError(f"Query references disallowed schemas: {sorted(disallowed)}")

    allowed_tables = _normalized_set(effective_policy.allowed_tables)
    if allowed_tables is not None:
        query_tables = _extract_tables(statement)
        disallowed = query_tables - allowed_tables
        if disallowed:
            raise SQLPolicyError(f"Query references disallowed tables: {sorted(disallowed)}")
