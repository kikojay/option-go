"""
交易日志服务 — 只碰 TRADING + INVESTMENT

数据来源：transactions 表（category_in=[TRADING, INVESTMENT]）
提供交易汇总指标和明细数据。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import pandas as pd
import streamlit as st

import db
from config import (
    TransactionCategory,
    OPTION_ACTIONS,
    ACTION_CN,
)


class TradingService:
    """
    交易日志服务

    提供交易指标汇总和明细表格数据。
    """

    @staticmethod
    @st.cache_data(ttl=300)
    def load(usd_rmb: float) -> Optional[pd.DataFrame]:
        """
        加载投资交易记录，附加 amount_rmb 列

        Args:
            usd_rmb: 美元兑人民币汇率

        Returns:
            带 amount_rmb/date 列的 DataFrame，无数据返回 None
        """
        raw = db.transactions.query(
            category_in=[TransactionCategory.TRADING, TransactionCategory.INVESTMENT],
            limit=2000,
        )
        if not raw:
            return None

        df = pd.DataFrame(raw)
        df["date"] = pd.to_datetime(df["datetime"])

        def _real_amount(row: pd.Series) -> float:
            """计算实际金额（期权要乘 100）"""
            mult = 100 if row["action"] in OPTION_ACTIONS else 1
            return (row.get("price") or 0) * (row.get("quantity") or 0) * mult * usd_rmb

        df["amount_rmb"] = df.apply(_real_amount, axis=1)
        return df

    @staticmethod
    def metrics(df: pd.DataFrame) -> Dict[str, float]:
        """
        交易汇总指标：买入/卖出/权利金/手续费

        Returns:
            {buy, sell, prem_in, prem_out, fees}
        """
        buy   = df[df["action"].isin(["BUY", "ASSIGNMENT"])]["amount_rmb"].sum()
        sell  = df[df["action"].isin(["SELL", "CALLED_AWAY"])]["amount_rmb"].sum()
        p_in  = df[df["action"].isin(["STO", "STO_CALL"])]["amount_rmb"].sum()
        p_out = df[df["action"].isin(["STC", "BTC", "BTO_CALL"])]["amount_rmb"].sum()

        # 手续费需单独乘汇率（原始是 USD）
        # 这里的 amount_rmb 已含汇率系数，费用手动读 df
        # 但原始逻辑是 fees.sum() * usd_rmb，这里从 df 第一行推算汇率
        # 更安全的方式：直接从外面传入
        fees = df["fees"].sum()
        # 推算 usd_rmb：取 amount_rmb 和原始数的比
        # 但原实现直接用 self.usd_rmb 乘，这里假设 usd_rmb 在 load 时已确定
        # 从同一个 df 读取的 amount_rmb 行信息还原
        if not df.empty:
            # 取第一条股票交易来推算汇率
            sample = df[df["action"].isin(["BUY", "SELL"])].head(1)
            if not sample.empty:
                row = sample.iloc[0]
                raw_amount = (row.get("price") or 0) * (row.get("quantity") or 0)
                if raw_amount > 0:
                    ratio = row["amount_rmb"] / raw_amount
                    fees = fees * ratio

        return {
            "buy": buy, "sell": sell,
            "prem_in": p_in, "prem_out": p_out,
            "fees": fees,
        }

    @staticmethod
    def detail(
        df: pd.DataFrame,
        stock_label_fn: Callable[[str], str],
    ) -> pd.DataFrame:
        """
        交易明细 DataFrame（前端就绪）

        Args:
            df:             load() 返回的 DataFrame
            stock_label_fn: 股票代码 → 带公司名的标签函数

        Returns:
            DataFrame(date, symbol, action_label, quantity, price, fees, currency, amount_rmb)
        """
        d = df[["date", "symbol", "action", "quantity", "price",
                "fees", "currency", "amount_rmb"]].copy()
        d["date"] = d["date"].dt.strftime("%Y-%m-%d")
        d["symbol"] = d["symbol"].map(stock_label_fn)
        d["action_label"] = d["action"].map(lambda a: ACTION_CN.get(a, a))
        return d[[
            "date",
            "symbol",
            "action_label",
            "quantity",
            "price",
            "fees",
            "currency",
            "amount_rmb",
        ]]
