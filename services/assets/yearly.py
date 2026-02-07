"""
年度汇总服务

数据来源：yearly_summary 表
提供年度数据加载和累计汇总。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

import db


class YearlyService:
    """
    年度汇总服务

    提供年度数据 DataFrame 和累计汇总指标。
    """

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_data() -> Optional[pd.DataFrame]:
        """
        加载年度汇总并转成 DataFrame

        Returns:
            带 年份 列的 DataFrame，或 None
        """
        summaries = db.yearly.get_all()
        if not summaries:
            return None
        df = pd.DataFrame(summaries)
        df["年份"] = df["year"].astype(str)
        return df

    @staticmethod
    def totals(df: pd.DataFrame) -> Dict[str, float]:
        """
        N 年累计汇总

        Returns:
            {pre_tax, post_tax, social, tax, invest, n_years}
        """
        return {
            "pre_tax":  df["pre_tax_income"].sum(),
            "post_tax": df["post_tax_income"].sum(),
            "social":   df["social_insurance"].sum(),
            "tax":      df["income_tax"].sum(),
            "invest":   df["investment_income"].sum(),
            "n_years":  len(df),
        }
