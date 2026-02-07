"""
车轮策略服务 — 业务调度层

只碰 TRADING 类别。返回裸数字，不含 $ / % 格式化。
负责：
1. load() — 从 DB 拉数据，创建 Calculator
2. overview_rows() — 调度 Calculator 生成概览
3. detail_metrics()  / cost_timeline() / trade_details() — 调度
4. recovery() — 获取实时价格 + 调度 Calculator 数学

图表方法通过 _WheelChartsMixin 注入。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

import db
from config import (
    TransactionCategory,
    OPTION_ACTIONS,
    STOCK_ACTIONS,
    YIELD_ACTIONS,
)
from services._legacy import WheelStrategyCalculator as LegacyWheelCalc
from services._legacy import dict_to_transaction as _legacy_dict_to_tx
from api.stock_data import get_current_price

from .calculator import WheelCalculator
from .charts import _WheelChartsMixin

# 车轮周期状态映射
_WHEEL_STATUS = {
    "holding": "持股中 · 卖Call",
    "waiting": "等待接盘 · 卖Put",
    "empty": "无交易",
}


class WheelService(_WheelChartsMixin):
    """
    车轮策略服务

    只碰 TRADING 类别。所有返回值为裸数字/dict/DataFrame，
    不含 $ / % 等格式化字符串。
    """

    # ─── 数据加载 ───

    @staticmethod
    @st.cache_data(ttl=300)
    def load() -> Optional[Dict[str, Any]]:
        """加载车轮页面全部数据"""
        tx_raw = db.transactions.query(
            category_in=[TransactionCategory.TRADING],
            action_in=OPTION_ACTIONS | STOCK_ACTIONS | YIELD_ACTIONS,
            limit=5000,
        )
        if not tx_raw:
            return None

        syms = WheelCalculator.get_strategy_symbols(tx_raw)
        if not syms:
            return None

        all_relevant = [
            t for t in tx_raw
            if t.get("symbol") in syms
            and t.get("action") in (OPTION_ACTIONS | STOCK_ACTIONS | {"DIVIDEND"})
        ]
        txns = [_legacy_dict_to_tx(t) for t in all_relevant]
        legacy_calc = LegacyWheelCalc(txns)

        return {
            "option_symbols": syms,
            "all_relevant": all_relevant,
            "transactions": txns,
            "wheel_calc": legacy_calc,
            "tx_raw": tx_raw,
        }

    # ─── 标的概览（裸数字） ───

    @staticmethod
    def overview_rows(
        syms: list,
        all_relevant: list,
        wheel_calc: LegacyWheelCalc,
        label_fn: Callable[[str], str],
    ) -> List[dict]:
        """
        车轮标的概览行 — 返回裸数字，由 UI 层格式化

        Returns:
            [{symbol, label, status, shares, cost_per_share,
              adjusted_cost_per_share, net_premium,
              annualized_pct, days_held}, ...]
        """
        rows = []
        for sym in syms:
            m = WheelCalculator.symbol_metrics(sym, all_relevant, wheel_calc)
            rows.append({
                "symbol": sym,
                "label": label_fn(sym),
                "status": _WHEEL_STATUS.get(m["status"], "—"),
                "shares": m["shares"],
                "cost_per_share": (
                    round(m["cost_basis"] / m["shares"], 2)
                    if m["shares"] else None
                ),
                "adjusted_cost_per_share": (
                    round(m["adjusted_cost"], 2)
                    if m["shares"] else None
                ),
                "net_premium": m["net_premium"],
                "annualized_pct": m["annualized_pct"],
                "days_held": m["days_held"],
            })
        return rows

    # ─── 选中标的 ───

    @staticmethod
    def detail_metrics(
        selected: str,
        all_relevant: list,
        wheel_calc: LegacyWheelCalc,
    ) -> Dict[str, Any]:
        """选中标的核心指标"""
        m = WheelCalculator.symbol_metrics(selected, all_relevant, wheel_calc)
        return {
            "net_prem": m["net_premium"],
            "collected": m["collected"],
            "paid": m["paid"],
            "cost_basis": m["cost_basis"],
            "adj_cost": m["adjusted_cost"],
            "shares": m["shares"],
            "fees": sum(
                _legacy_dict_to_tx(t).fees
                for t in all_relevant if t["symbol"] == selected
            ),
        }

    @staticmethod
    def cost_timeline(selected: str, all_relevant: list) -> List[dict]:
        """成本基准变化时间线（委托给 Calculator）"""
        return WheelCalculator.cost_timeline(selected, all_relevant)

    @staticmethod
    def trade_details(
        selected: str,
        all_relevant: list,
    ) -> tuple:
        """逐笔期权交易明细 — 裸数字（委托给 Calculator）"""
        return WheelCalculator.trade_pnl_series(selected, all_relevant)

    # ─── 盈亏分析 & 回本预测 ───

    @staticmethod
    def recovery(
        selected: str,
        all_relevant: list,
        wheel_calc: LegacyWheelCalc,
    ) -> Optional[Dict[str, Any]]:
        """盈亏分析 & 回本预测"""
        m = WheelCalculator.symbol_metrics(selected, all_relevant, wheel_calc)
        shares = m["shares"]
        cb = m["cost_basis"]

        if shares <= 0 or cb <= 0:
            return None

        stock_cost = WheelCalculator.compute_stock_cost(selected, all_relevant)
        divs = WheelCalculator.compute_dividends(selected, all_relevant)
        weeks = WheelCalculator.compute_option_weeks(selected, all_relevant)

        recovery = WheelCalculator.recovery_prediction(
            stock_cost, m["net_premium"], divs, weeks,
        )
        if recovery is None:
            return None

        # 补充实时价格（唯一的 API 副作用）
        try:
            cur_info = get_current_price(selected)
            cur_price = cur_info.get("price", 0) if cur_info else 0
        except Exception:
            cur_price = 0

        return {
            "stock_cost": stock_cost,
            "net_basis": recovery["net_basis"],
            "nb_per_share": recovery["net_basis"] / shares if shares else 0,
            "cur_price": cur_price,
            "dividends": divs,
            "avg_weekly": recovery["avg_weekly"],
            "weeks_to_zero": recovery["weeks_to_zero"],
            "progress": recovery["progress"],
            "net_prem": m["net_premium"],
        }
