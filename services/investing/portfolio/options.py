"""
投资组合 — 期权策略 Tab (mixin)

提供 get_option_symbols / get_all_relevant_tx /
build_options_overview / build_option_detail 给 PortfolioService 使用。

复用 WheelCalculator 的纯数学计算（weeks_to_zero / cost_timeline）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List

from config import OPTION_ACTIONS, STOCK_ACTIONS
from services._legacy import WheelStrategyCalculator
from services.investing.strategies.wheel.calculator import WheelCalculator


class _OptionsMixin:
    """期权策略相关方法（Tab 3），通过 mixin 注入 PortfolioService"""

    @staticmethod
    def get_option_symbols(tx_raw: list) -> List[str]:
        """有期权交易的标的列表（排序）"""
        return WheelCalculator.get_strategy_symbols(tx_raw)

    @staticmethod
    def get_all_relevant_tx(tx_raw: list, symbols: list) -> list:
        """期权标的相关全部交易（含股票/分红）"""
        return [
            t for t in tx_raw
            if t.get("symbol") in symbols
            and t.get("action") in (OPTION_ACTIONS | STOCK_ACTIONS | {"DIVIDEND"})
        ]

    @staticmethod
    def build_options_overview(
        symbols: list,
        all_relevant: list,
        wheel_calc: WheelStrategyCalculator,
        stock_label_fn: Callable[[str], str],
    ) -> List[Dict[str, Any]]:
        """
        期权标的总览表行

        Returns:
            list of dicts — 每行含 symbol_label/status_label/shares 等
        """
        _status = {
            "holding": "持股中 · 卖 Call",
            "waiting": "等待接盘 · 卖 Put",
            "empty": "无交易",
        }
        rows = []
        for sym in symbols:
            m = WheelCalculator.symbol_metrics(sym, all_relevant, wheel_calc)
            divs = WheelCalculator.compute_dividends(sym, all_relevant)
            w2z = WheelCalculator.weeks_to_zero(
                sym, all_relevant, m["cost_basis"], m["net_premium"], divs,
            )

            rows.append({
                "symbol_label": stock_label_fn(sym),
                "status_label": _status.get(m["status"], "—"),
                "shares": m["shares"],
                "net_premium": m["net_premium"],
                "dividends": divs,
                "adjusted_cost_per_share": m["adjusted_cost"] if m["shares"] else None,
                "annualized_pct": m["annualized_pct"],
                "weeks_to_zero": round(w2z, 1) if w2z != float("inf") else None,
                "days_held": m["days_held"],
            })
        return rows

    @staticmethod
    def build_option_detail(
        selected: str,
        all_relevant: list,
        wheel_calc: WheelStrategyCalculator,
    ) -> Dict[str, Any]:
        """
        选定标的期权详情

        Returns:
            {net_prem, collected, paid, cost_basis, adj_cost, shares,
             dividends, recovery, cost_timeline}
        """
        m = WheelCalculator.symbol_metrics(selected, all_relevant, wheel_calc)
        divs = WheelCalculator.compute_dividends(selected, all_relevant)

        # 回本预测
        recovery = None
        if m["shares"] > 0 and m["cost_basis"] > 0:
            stock_cost = WheelCalculator.compute_stock_cost(
                selected, all_relevant,
            )
            weeks = WheelCalculator.compute_option_weeks(
                selected, all_relevant,
            )
            rp = WheelCalculator.recovery_prediction(
                stock_cost, m["net_premium"], divs, weeks,
            )
            if rp is not None:
                recovery = {
                    "avg_weekly": rp["avg_weekly"],
                    "remaining": rp["net_basis"],
                    "weeks_to_zero": rp["weeks_to_zero"],
                    "months_to_zero": rp["months_to_zero"],
                    "progress": rp["progress"],
                    "net_prem": m["net_premium"],
                    "dividends": divs,
                    "cost_basis": m["cost_basis"],
                }

        tl = WheelCalculator.cost_timeline(selected, all_relevant)

        return {
            "net_prem": m["net_premium"],
            "collected": m["collected"],
            "paid": m["paid"],
            "cost_basis": m["cost_basis"],
            "adj_cost": m["adjusted_cost"],
            "shares": m["shares"],
            "dividends": divs,
            "recovery": recovery,
            "cost_timeline": tl,
        }
