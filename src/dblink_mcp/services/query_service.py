from typing import Dict, Optional

import pandas as pd

from dblink_mcp.config.models import QueryPolicyConfig
from dblink_mcp.security.sql_policy import evaluate_sql_policy


async def execute_query(connector, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
    policy_dict = connector.connection_config.get("policy") if connector.connection_config else None
    policy = QueryPolicyConfig.model_validate(policy_dict or {})

    evaluate_sql_policy(query, policy)

    dataframe = await connector.execute_query(query, params)
    if policy.max_rows is not None and len(dataframe) > policy.max_rows:
        raise ValueError(
            f"Query returned {len(dataframe)} rows, exceeding configured max_rows={policy.max_rows}"
        )

    return dataframe
