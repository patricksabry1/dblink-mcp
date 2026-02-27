from __future__ import annotations

from typing import Any, Dict

import pandas as pd


class DataComparator:
    @staticmethod
    def compare_dataframes(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        name1: str = "DataFrame1",
        name2: str = "DataFrame2",
    ) -> Dict[str, Any]:
        comparison = {
            "row_count_match": len(df1) == len(df2),
            "row_count_df1": len(df1),
            "row_count_df2": len(df2),
            "column_count_match": len(df1.columns) == len(df2.columns),
            "column_count_df1": len(df1.columns),
            "column_count_df2": len(df2.columns),
            "column_names_match": list(df1.columns) == list(df2.columns),
            "column_names_df1": list(df1.columns),
            "column_names_df2": list(df2.columns),
            "data_types_match": True,
            "data_types_differences": [],
            "data_content_match": False,
            "content_differences": [],
        }

        if comparison["column_names_match"]:
            for col in df1.columns:
                if col in df2.columns and df1[col].dtype != df2[col].dtype:
                    comparison["data_types_match"] = False
                    comparison["data_types_differences"].append(
                        {
                            "column": col,
                            f"{name1}_dtype": str(df1[col].dtype),
                            f"{name2}_dtype": str(df2[col].dtype),
                        }
                    )

        if comparison["row_count_match"] and comparison["column_names_match"] and comparison["data_types_match"]:
            comparison["data_content_match"] = df1.equals(df2)
            if not comparison["data_content_match"]:
                comparison["content_differences"] = [col for col in df1.columns if not df1[col].equals(df2[col])]

        return comparison

    @staticmethod
    def detect_schema_differences(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, Any]:
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        common_cols = cols1.intersection(cols2)

        return {
            "columns_only_in_df1": list(cols1 - cols2),
            "columns_only_in_df2": list(cols2 - cols1),
            "common_columns": list(common_cols),
            "dtype_differences": [
                {
                    "column": col,
                    "df1_dtype": str(df1[col].dtype),
                    "df2_dtype": str(df2[col].dtype),
                }
                for col in common_cols
                if df1[col].dtype != df2[col].dtype
            ],
        }
