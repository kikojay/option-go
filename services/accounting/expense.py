"""
收支管理服务 — 只碰 INCOME + EXPENSE

数据来源：transactions 表（category_in=[INCOME, EXPENSE]）
彻底使用正向 category 过滤，不再依赖旧的反向 _INVEST_ACTIONS 排除。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

import db
from config import TransactionCategory


class ExpenseService:
    """
    收支管理服务

    提供年度汇总、月度趋势、分类统计、明细等方法。
    所有方法为 @staticmethod，数据库查询通过 db.transactions.query() 完成。
    """

    @staticmethod
    @st.cache_data(ttl=600)
    def load(usd_rmb: float, hkd_rmb: float = 1.0) -> Optional[pd.DataFrame]:
        """
        加载 INCOME + EXPENSE 类交易，附加 amount_rmb / month / year 列

        Args:
            usd_rmb: 美元兑人民币汇率（用于金额换算）
            hkd_rmb: 港币兑人民币汇率

        Returns:
            带 amount_rmb/month/year 列的 DataFrame，无数据返回 None
        """
        raw = db.transactions.query(
            category_in=[TransactionCategory.INCOME, TransactionCategory.EXPENSE],
            limit=5000,
        )
        if not raw:
            return None

        df = pd.DataFrame(raw)
        if df.empty:
            return None

        df["date"]  = pd.to_datetime(df["datetime"])
        df["month"] = df["date"].dt.strftime("%Y-%m")
        df["year"]  = df["date"].dt.year

        def _currency_rate(currency: str) -> float:
            """币种 → 人民币汇率倍数"""
            if currency == "USD":
                return usd_rmb
            if currency == "HKD":
                return hkd_rmb
            return 1.0  # CNY

        df["amount_rmb"] = df.apply(
            lambda x: (x.get("price") or 0) * _currency_rate(x.get("currency", "CNY")),
            axis=1,
        )
        return df

    @staticmethod
    def year_summary(df: pd.DataFrame, year: int) -> Dict[str, float]:
        """
        年度收入/支出/净额/储蓄率

        Returns:
            {income, expense, net, save_rate, year}
        """
        ydf = df[df["year"] == year]
        income  = ydf[ydf["action"] == "INCOME"]["amount_rmb"].sum()
        expense = ydf[ydf["action"] == "EXPENSE"]["amount_rmb"].sum()
        net     = income - expense
        rate    = (net / income * 100) if income > 0 else 0
        return {
            "income": income, "expense": expense,
            "net": net, "save_rate": rate, "year": year,
        }

    @staticmethod
    def monthly_trend(df: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        按月汇总 INCOME/EXPENSE/NET，用于柱+线图

        Returns:
            DataFrame（index=month, columns=[INCOME, EXPENSE, NET]）
        """
        ydf = df[df["year"] == year]
        agg = ydf.groupby(["month", "action"])["amount_rmb"].sum().unstack(fill_value=0)
        for col in ("INCOME", "EXPENSE"):
            if col not in agg.columns:
                agg[col] = 0
        agg = agg.sort_index()
        agg["NET"] = agg["INCOME"] - agg["EXPENSE"]
        return agg

    @staticmethod
    def month_summary(df: pd.DataFrame, month: str) -> Dict[str, float]:
        """
        单月收入/支出/净额/储蓄率

        Returns:
            {income, expense, net, save_rate}
        """
        mdf = df[df["month"] == month]
        income  = mdf[mdf["action"] == "INCOME"]["amount_rmb"].sum()
        expense = mdf[mdf["action"] == "EXPENSE"]["amount_rmb"].sum()
        net     = income - expense
        rate    = (net / income * 100) if income > 0 else 0
        return {"income": income, "expense": expense, "net": net, "save_rate": rate}

    @staticmethod
    def category_groups(
        df: pd.DataFrame,
        month: str,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        分类饼图数据

        Returns:
            (支出分组 Series, 收入分组 Series)
        """
        mdf = df[df["month"] == month]
        exp = (mdf[mdf["action"] == "EXPENSE"]
               .groupby("subcategory")["amount_rmb"]
               .sum().sort_values(ascending=False))
        inc = (mdf[mdf["action"] == "INCOME"]
               .groupby("subcategory")["amount_rmb"]
               .sum().sort_values(ascending=False))
        return exp, inc

    @staticmethod
    def detail(df: pd.DataFrame, month: str) -> pd.DataFrame:
        """
        月度明细 DataFrame（前端就绪）

        Returns:
            DataFrame(date, action_label, subcategory, amount_display, note)
        """
        mdf = df[df["month"] == month]
        cols_available = ["date", "action", "subcategory", "price", "currency", "note"]
        # 兼容可能缺少的列
        use_cols = [c for c in cols_available if c in mdf.columns]
        d = mdf[use_cols].copy()
        d["date"] = d["date"].dt.strftime("%Y-%m-%d")
        d["action_label"] = d["action"].map({
            "INCOME": "收入",
            "EXPENSE": "支出",
        }).fillna(d["action"])
        d["amount_display"] = d.apply(
            lambda r: f"{r.get('price', 0):,.2f} {r.get('currency', 'CNY')}", axis=1
        )
        return d[["date", "action_label", "subcategory", "amount_display", "note"]].copy()
