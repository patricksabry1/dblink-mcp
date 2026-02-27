from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd


class DatabaseConnector(ABC):
    """Abstract base class for all database connectors."""

    def __init__(self, connection_config: Dict[str, Any]):
        self.connection_config = connection_config
        self.connection = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish a database connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection."""

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute query and return results as a DataFrame."""

    def validate_readonly_query(self, query: str) -> bool:
        """Validate that query appears to be read-only."""
        query_upper = query.strip().upper()
        readonly_keywords = ["SELECT", "WITH", "SHOW", "DESCRIBE", "DESC"]
        forbidden_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "MERGE",
        ]

        starts_with_readonly = any(query_upper.startswith(keyword) for keyword in readonly_keywords)
        contains_forbidden = any(keyword in query_upper for keyword in forbidden_keywords)
        return starts_with_readonly and not contains_forbidden

    def apply_query_limit(self, query: str, limit: int) -> str:
        """Apply default LIMIT syntax for engines that support it."""
        if any(keyword in query.upper() for keyword in ["LIMIT", "ROWNUM", "TOP"]):
            return query
        return f"{query.rstrip(';')} LIMIT {limit}"
