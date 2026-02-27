from typing import Optional, Set

from pydantic import BaseModel, Field


class QueryPolicyConfig(BaseModel):
    allowed_schemas: Optional[Set[str]] = Field(default=None)
    allowed_tables: Optional[Set[str]] = Field(default=None)
    max_rows: Optional[int] = Field(default=None, ge=1)
    allowed_statement_types: Set[str] = Field(default_factory=lambda: {"select"})


class BaseConnectionConfig(BaseModel):
    user: str
    password: str
    policy: QueryPolicyConfig = Field(default_factory=QueryPolicyConfig)


class SnowflakeConnectionConfig(BaseConnectionConfig):
    account: str
    warehouse: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None


class OracleConnectionConfig(BaseConnectionConfig):
    host: str
    port: int
    service_name: str


class PostgreSQLConnectionConfig(BaseConnectionConfig):
    host: str
    port: int
    database: str
