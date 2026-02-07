"""
车轮策略计算器 — 继承 BaseStrategyCalculator

只需实现 2 个抽象方法（get_strategy_symbols / symbol_metrics），
其余通用原子操作（cost_timeline / recovery / trade_pnl / dividends 等）
全部继承自基类，开箱即用。

子类可 override 任何基类方法来定制行为。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from config import OPTION_ACTIONS
from services.investing.strategies.base import BaseStrategyCalculator


class WheelCalculator(BaseStrategyCalculator):
    """
    车轮策略计算器

    仅实现策略差异点（symbol_metrics 依赖 legacy_calc 的车轮特有逻辑），
    所有通用计算直接继承 BaseStrategyCalculator。
    """

    @staticmethod
    def get_strategy_symbols(transactions: list) -> List[str]:
        """获取有期权交易的标的列表"""
        return sorted(set(
            t["symbol"] for t in transactions
            if t.get("action") in OPTION_ACTIONS and t.get("symbol")
        ))

    @staticmethod
    def symbol_metrics(
        symbol: str,
        transactions: list,
        legacy_calc: Any = None,
    ) -> Dict[str, Any]:
        """
        计算单个标的核心指标（裸数字）

        依赖 legacy_calc（src.options.WheelStrategyCalculator 实例）
        来获取车轮特有的 adjusted_cost_basis 和 wheel_cycle_info。

        Returns:
            {cost_basis, net_premium, adjusted_cost, shares,
             collected, paid, status, annualized_pct, days_held}
        """
        basis = legacy_calc.calculate_adjusted_cost_basis(symbol)
        prem = legacy_calc.option_calc.get_premiums_summary(symbol)
        cycle = legacy_calc.get_wheel_cycle_info(symbol)
        shares = int(basis.get("current_shares", 0))

        np_ = prem.get("net_premium", 0)
        cb = basis.get("cost_basis", 0)
        days = BaseStrategyCalculator.compute_days_held(symbol, transactions)
        ann = BaseStrategyCalculator.annualized_return(np_, cb, days)

        return {
            "cost_basis": cb,
            "net_premium": np_,
            "adjusted_cost": basis.get("adjusted_cost", 0),
            "shares": shares,
            "collected": prem.get("total_collected", 0),
            "paid": prem.get("total_paid", 0),
            "status": cycle.get("status", ""),
            "annualized_pct": ann,
            "days_held": days,
        }
