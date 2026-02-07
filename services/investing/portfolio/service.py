"""
投资组合服务 — 只碰 TRADING + INVESTMENT

数据来源：transactions 表（category_in=[TRADING, INVESTMENT]）
合并原 FinanceEngine.portfolio_* + PortfolioService 的成熟实现。

提供 4 个子 Tab 的数据：
1. 总览 — 核心指标 + 趋势图
2. 持仓明细 — 逐标的行 + 合计（holdings.py）
3. 期权策略 — 标的总览 + 选定标的详情（options.py）
4. 资金流 — 入金/出金历史

预留接口：
- get_net_inflow()（§2.10.1 净投入追踪）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import db
from config import (
    TransactionCategory,
    CAPITAL_ACTIONS,
)
from services._legacy import PortfolioCalculator, dict_to_transaction as _legacy_dict_to_tx
from api.stock_data import get_batch_prices

# 内部辅助函数
from ._helpers import (
    cumulative_deposits as _cumulative_deposits,
    estimate_deposits as _estimate_deposits,
)

# Mixin：持仓明细 + 期权策略
from .holdings import _HoldingsMixin
from .options import _OptionsMixin


class PortfolioService(_HoldingsMixin, _OptionsMixin):
    """
    投资组合服务

    提供投资组合全部数据计算和准备。
    所有方法为 @staticmethod。
    Tab 2（持仓）和 Tab 3（期权）方法通过 Mixin 注入。
    """

    # ═══════════════════════════════════════════════════
    #  1. 数据加载
    # ═══════════════════════════════════════════════════

    @staticmethod
    @st.cache_data(ttl=600)
    def load_base(usd_rmb: float) -> Optional[Dict[str, Any]]:
        """
        加载投资组合基础数据（不含行情）

        Args:
            usd_rmb: 美元兑人民币汇率

        Returns:
            {usd_rmb, tx_raw, transactions, calc, summary,
             holdings, capital_flows}
            无数据时返回 None
        """
        tx_raw = db.transactions.query(
            category_in=[TransactionCategory.TRADING, TransactionCategory.INVESTMENT],
            limit=5000,
        )
        if not tx_raw:
            return None

        # 转 legacy Transaction 模型（PortfolioCalculator 依赖旧 Transaction）
        transactions = [_legacy_dict_to_tx(t) for t in tx_raw]
        calc = PortfolioCalculator(transactions)
        summary = calc.get_portfolio_summary()
        holdings = summary.get("holdings", {})

        # 入金/出金记录
        capital_flows = [
            t for t in tx_raw if t.get("action") in CAPITAL_ACTIONS
        ]

        return {
            "usd_rmb": usd_rmb,
            "tx_raw": tx_raw,
            "transactions": transactions,
            "calc": calc,
            "summary": summary,
            "holdings": holdings,
            "capital_flows": capital_flows,
        }

    @staticmethod
    @st.cache_data(ttl=300)
    def get_live_prices(symbols: List[str]) -> Dict[str, Any]:
        """
        获取实时行情（单独缓存）

        Args:
            symbols: 标的列表

        Returns:
            {symbol: price_info, ...}
        """
        if not symbols:
            return {}
        uniq = sorted(set(symbols))
        try:
            return get_batch_prices(uniq)
        except Exception:
            return {}

    @staticmethod
    def load(usd_rmb: float) -> Optional[Dict[str, Any]]:
        """
        加载投资组合全部数据（基础数据 + 行情）

        Args:
            usd_rmb: 美元兑人民币汇率

        Returns:
            {usd_rmb, tx_raw, transactions, calc, summary,
             holdings, live_prices, capital_flows}
            无数据时返回 None
        """
        base = PortfolioService.load_base(usd_rmb)
        if base is None:
            return None

        symbols_with_shares = [
            sym for sym, h in base.get("holdings", {}).items()
            if int(h.get("current_shares", 0)) > 0
        ]
        live_prices = PortfolioService.get_live_prices(symbols_with_shares)

        return {
            **base,
            "live_prices": live_prices,
        }

    # ═══════════════════════════════════════════════════
    #  2. 总览 Tab — 指标 + 趋势
    # ═══════════════════════════════════════════════════

    @staticmethod
    def calc_overview_metrics(data: dict) -> Dict[str, Any]:
        """
        计算总览页核心指标

        Returns:
            {total_value, total_cost, total_pnl, total_premiums, usd_rmb}
        """
        holdings = data["holdings"]
        live_prices = data["live_prices"]
        summary = data["summary"]
        usd_rmb = data["usd_rmb"]

        total_value = 0.0
        for sym, h in holdings.items():
            shares = int(h.get("current_shares", 0))
            if shares > 0:
                lp = live_prices.get(sym, {}).get("price", 0)
                total_value += (
                    lp * shares if lp
                    else h.get("market_value", 0) or h.get("cost_basis", 0)
                )
            else:
                total_value += h.get("market_value", 0) or 0

        total_cost = sum(h.get("cost_basis", 0) for h in holdings.values())
        total_pnl = summary.get("total_unrealized_pnl", 0)
        total_premiums = sum(
            h.get("total_premiums", 0) for h in holdings.values()
        )

        return {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_premiums": total_premiums,
            "usd_rmb": usd_rmb,
        }

    @staticmethod
    def build_capital_flow_table(capital_flows: list) -> Optional[pd.DataFrame]:
        """
        入金/出金历史 DataFrame

        Returns:
            DataFrame(date, action_label, amount_usd, note) 或 None
        """
        if not capital_flows:
            return None
        cf = pd.DataFrame(capital_flows)
        cf = cf[cf["action"].isin(CAPITAL_ACTIONS)]
        if cf.empty:
            return None
        d = cf[["datetime", "action", "price", "note"]].copy()
        d["date"] = pd.to_datetime(d["datetime"]).dt.strftime("%Y-%m-%d")
        d["action_label"] = d["action"].map({
            "DEPOSIT": "入金",
            "WITHDRAW": "出金",
        })
        d = d.rename(columns={"price": "amount_usd"})
        return d[["date", "action_label", "amount_usd", "note"]]

    @staticmethod
    def build_trend_data(data: dict) -> Optional[pd.DataFrame]:
        """
        总资产增长 + 本金 + 真实收益合并 DataFrame

        Returns:
            DataFrame(date, total_usd, deposit, gain, twr_pct) 或 None
        """
        snapshots = db.snapshots.get_all()
        if not snapshots:
            return None

        sdf = pd.DataFrame(snapshots)
        sdf["date_parsed"] = pd.to_datetime(sdf["date"])
        sdf = sdf.sort_values("date_parsed")
        sdf["total_usd"] = sdf["total_assets_usd"]
        sdf["date"] = sdf["date_parsed"].dt.strftime("%Y-%m-%d")

        flows = data.get("capital_flows", [])
        dep = (
            _cumulative_deposits(flows)
            if flows
            else _estimate_deposits(data["tx_raw"])
        )

        if dep:
            dep_df = pd.DataFrame(dep).drop_duplicates(
                subset="date", keep="last",
            )
            dep_df["date_parsed"] = pd.to_datetime(dep_df["date"])
            merged = pd.merge_asof(
                sdf.sort_values("date_parsed"),
                dep_df[["date_parsed", "deposit"]].sort_values("date_parsed"),
                on="date_parsed",
                direction="backward",
            )
            merged["deposit"] = merged["deposit"].fillna(0)
            merged["gain"] = merged["total_usd"] - merged["deposit"]
        else:
            merged = sdf.copy()
            merged["deposit"] = 0
            merged["gain"] = merged["total_usd"]

        # TWR 近似
        merged["twr_pct"] = merged.apply(
            lambda r: ((r["total_usd"] - r["deposit"]) / r["deposit"] * 100)
            if r["deposit"] > 0 else 0,
            axis=1,
        )
        return merged

    # ═══════════════════════════════════════════════════
    #  预留接口 — 净投入追踪（§2.10.1）
    # ═══════════════════════════════════════════════════

    @staticmethod
    def get_net_inflow() -> Dict[str, float]:
        """
        计算净投入（预留接口）

        - total_deposited:  历史累计入金总额
        - total_withdrawn:  历史累计出金总额
        - net_inflow:       净投入 = deposited - withdrawn
        """
        deposits = db.transactions.query(
            category_in=[TransactionCategory.INVESTMENT],
            action_in={"DEPOSIT"},
            limit=10000,
        )
        withdrawals = db.transactions.query(
            category_in=[TransactionCategory.INVESTMENT],
            action_in={"WITHDRAW"},
            limit=10000,
        )
        total_deposited = sum(t.get("price", 0) for t in deposits)
        total_withdrawn = sum(t.get("price", 0) for t in withdrawals)
        return {
            "total_deposited": total_deposited,
            "total_withdrawn": total_withdrawn,
            "net_inflow": total_deposited - total_withdrawn,
        }
