"""
期权策略基类 — 通用原子计算 + 策略差异抽象

子类只需实现 get_strategy_symbols / symbol_metrics，
其余原子操作（分红/成本/回本预测等）直接继承可用。
纯数学，无 DB / UI 依赖。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import OPTION_ACTIONS


class BaseStrategyCalculator(ABC):
    """策略计算器基类 — 抽象方法 + 通用原子操作，子类可 override"""

    # ─── 抽象方法 ───

    @staticmethod
    @abstractmethod
    def get_strategy_symbols(transactions: list) -> List[str]:
        """提取与本策略相关的标的列表"""
        ...

    @staticmethod
    @abstractmethod
    def symbol_metrics(
        symbol: str, transactions: list, legacy_calc: Any = None,
    ) -> Dict[str, Any]:
        """计算单个标的核心指标，返回裸数字"""
        ...

    # ─── 通用原子操作 ───

    @staticmethod
    def compute_dividends(symbol: str, transactions: list) -> float:
        """计算标的累计分红（所有策略通用）"""
        return sum(
            t.get("price", 0) * t.get("quantity", 1)
            for t in transactions
            if t.get("symbol") == symbol and t.get("action") == "DIVIDEND"
        )

    @staticmethod
    def compute_stock_cost(symbol: str, transactions: list) -> float:
        """计算标的股票购买总成本（BUY + ASSIGNMENT）"""
        return sum(
            t["price"] * t["quantity"]
            for t in transactions
            if t["symbol"] == symbol
            and t["action"] in ("BUY", "ASSIGNMENT")
        )

    @staticmethod
    def compute_current_shares(symbol: str, transactions: list) -> int:
        """计算标的当前持仓股数"""
        bought = sum(
            t.get("quantity", 0)
            for t in transactions
            if t["symbol"] == symbol
            and t["action"] in ("BUY", "ASSIGNMENT")
        )
        sold = sum(
            t.get("quantity", 0)
            for t in transactions
            if t["symbol"] == symbol
            and t["action"] in ("SELL", "CALLED_AWAY")
        )
        return bought - sold

    @staticmethod
    def compute_option_weeks(symbol: str, transactions: list) -> float:
        """计算期权交易跨度（周数）"""
        opts = [
            t for t in transactions
            if t["symbol"] == symbol and t["action"] in OPTION_ACTIONS
        ]
        if not opts:
            return 0
        dates = [t["datetime"][:10] for t in opts]
        first = datetime.strptime(min(dates), "%Y-%m-%d")
        last = datetime.strptime(max(dates), "%Y-%m-%d")
        return max((last - first).days / 7, 1)

    @staticmethod
    def compute_days_held(symbol: str, transactions: list) -> int:
        """计算标的持有天数（首笔交易至今）"""
        dates = [
            t["datetime"][:10] for t in transactions
            if t["symbol"] == symbol
        ]
        if not dates:
            return 0
        first = min(dates)
        return (datetime.now() - datetime.strptime(first, "%Y-%m-%d")).days

    @staticmethod
    def annualized_return(
        net_premium: float,
        cost_basis: float,
        days_held: int,
    ) -> float:
        """计算年化收益率 %（通用公式）"""
        if cost_basis <= 0 or days_held <= 0:
            return 0.0
        return round((net_premium / cost_basis) * (365 / days_held) * 100, 1)

    # ─── 成本时间线（默认实现，适用于单腿策略） ───

    @staticmethod
    def cost_timeline(symbol: str, transactions: list) -> List[dict]:
        """
        构建成本基准随时间变化的数据点列表

        默认实现：跟踪 股票买卖 + 期权收支 对每股成本的影响。
        多腿策略（如 Repair）可 override 此方法。

        Returns:
            [{date, cost_per_share, action}, ...]
        """
        sym_txs = sorted(
            [t for t in transactions if t["symbol"] == symbol],
            key=lambda t: t["datetime"],
        )
        rsc, rp, rf, rs = 0.0, 0.0, 0.0, 0
        timeline = []
        for t in sym_txs:
            a = t["action"]
            q = t.get("quantity", 0)
            p = t.get("price", 0)
            f = t.get("fees", 0)
            dt = t["datetime"][:10]
            if a in ("BUY", "ASSIGNMENT"):
                rsc += p * q
                rs += q
            elif a in ("SELL", "CALLED_AWAY"):
                rsc -= p * q
                rs -= q
            elif a in OPTION_ACTIONS:
                if a in ("STO", "STO_CALL"):
                    rp += p * q * 100
                else:
                    rp -= p * q * 100
            rf += f
            if rs > 0:
                timeline.append({
                    "date": dt,
                    "cost_per_share": round((rsc - rp + rf) / rs, 2),
                    "action": a,
                })
        return timeline

    # ─── 回本预测（默认实现） ───

    @staticmethod
    def recovery_prediction(
        stock_cost: float,
        net_premium: float,
        dividends: float,
        option_weeks: float,
    ) -> Optional[Dict[str, float]]:
        """
        回本预测（纯数学）

        默认实现：线性外推（周均权利金 × 剩余周数 = 回本时间）。
        适用于 Wheel / Repair 等持续收取权利金的策略。

        Returns:
            {avg_weekly, weeks_to_zero, months_to_zero, progress, net_basis}
            或 None
        """
        if stock_cost <= 0 or option_weeks <= 0:
            return None

        avg_weekly = net_premium / option_weeks
        net_basis = stock_cost - net_premium - dividends
        progress = min((net_premium + dividends) / stock_cost, 1.0)
        weeks_to_zero = (
            net_basis / avg_weekly if avg_weekly > 0 and net_basis > 0 else 0
        )

        return {
            "avg_weekly": avg_weekly,
            "weeks_to_zero": weeks_to_zero,
            "months_to_zero": weeks_to_zero / 4.33,
            "progress": progress,
            "net_basis": net_basis,
        }

    @staticmethod
    def weeks_to_zero(
        symbol: str,
        transactions: list,
        cost_basis: float,
        net_premium: float,
        dividends: float,
    ) -> float:
        """
        计算预计回本周数（简化版 recovery_prediction）

        直接返回 float，适合嵌入表格显示。
        """
        opts = [
            t for t in transactions
            if t["symbol"] == symbol and t.get("action") in OPTION_ACTIONS
        ]
        if opts and cost_basis > 0:
            dates = [t["datetime"][:10] for t in opts]
            first = datetime.strptime(min(dates), "%Y-%m-%d")
            last = datetime.strptime(max(dates), "%Y-%m-%d")
            weeks_active = max((last - first).days / 7, 1)
            avg_weekly = net_premium / weeks_active
            remaining = cost_basis - net_premium - dividends
            if avg_weekly > 0:
                return remaining / avg_weekly
        return float("inf")

    # ─── 逐笔 P&L（默认实现，适用于单腿期权策略） ───

    @staticmethod
    def trade_pnl_series(
        symbol: str,
        transactions: list,
    ) -> Tuple[List[dict], float]:
        """
        逐笔期权交易 P&L 明细（裸数字）

        默认实现：单腿期权（STO/BTC/STO_CALL/BTC_CALL）。
        多腿策略（如 Repair 的 1:2 Call Spread）应 override。

        Returns:
            (trades, cumulative_premium)
        """
        sym_txs = sorted(
            [t for t in transactions if t["symbol"] == symbol],
            key=lambda t: t["datetime"],
        )
        option_txs = [t for t in sym_txs if t["action"] in OPTION_ACTIONS]
        shares = BaseStrategyCalculator.compute_current_shares(
            symbol, transactions,
        )

        if not option_txs or shares <= 0:
            return [], 0.0

        buy_dates = [
            t["datetime"][:10] for t in sym_txs
            if t["action"] in ("BUY", "ASSIGNMENT")
        ]
        base_date = (
            datetime.strptime(min(buy_dates), "%Y-%m-%d")
            if buy_dates else datetime.now()
        )
        raw_cost = BaseStrategyCalculator.compute_stock_cost(
            symbol, transactions,
        )

        trades: List[dict] = []
        cumulative = 0.0
        for t in option_txs:
            act = t["action"]
            qty = t.get("quantity", 0)
            price = t.get("price", 0)
            fees = t.get("fees", 0)
            date = t["datetime"][:10]
            premium = price * qty * 100
            is_income = act in ("STO", "STO_CALL")
            net = premium - fees if is_income else -(premium + fees)
            cumulative += net
            days = max(
                (datetime.strptime(date, "%Y-%m-%d") - base_date).days, 1
            )
            single_pct = (abs(net) / raw_cost * 100) if raw_cost > 0 else 0
            ann = (
                (abs(net) / raw_cost) * (365 / days) * 100
                if raw_cost > 0 else 0
            )

            trades.append({
                "date": date,
                "action": act,
                "quantity": qty,
                "price_per_contract": price,
                "total_premium": premium,
                "fees": fees,
                "net_income": net,
                "is_income": is_income,
                "single_return_pct": round(single_pct, 2),
                "annualized_pct": round(ann, 1),
                "cumulative": cumulative,
            })
        return trades, cumulative
