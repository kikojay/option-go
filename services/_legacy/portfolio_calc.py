"""
组合计算器 — 汇总整个投资组合的盈亏和持仓
"""
from typing import List, Dict
from services._legacy.models import Transaction
from services._legacy.wheel_calc import WheelStrategyCalculator


class PortfolioCalculator:
    """
    投资组合计算器

    根据所有交易汇总整个组合的：
    - 所有持仓信息
    - 所有盈亏数据
    - 资产配比
    """

    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions
        self.wheel_calculator = WheelStrategyCalculator(transactions)

    def get_portfolio_summary(self, prices: Dict[str, float] = None) -> Dict:
        """获取组合汇总"""
        symbols = set(t.symbol for t in self.transactions if t.symbol)

        holdings = {}
        total_realized = 0
        total_unrealized = 0

        for symbol in symbols:
            summary = self.wheel_calculator.calculate_campaign_summary(
                symbol,
                prices.get(symbol) if prices else None
            )
            holdings[symbol] = summary
            total_realized += summary.get("option_pnl", 0)
            total_unrealized += summary.get("unrealized_pnl", 0)

        return {
            "holdings": holdings,
            "total_realized_pnl": total_realized,
            "total_unrealized_pnl": total_unrealized,
            "total_pnl": total_realized + total_unrealized
        }

    def get_asset_allocation(self, prices: Dict[str, float] = None) -> Dict[str, float]:
        """获取资产配置（各持仓占比）"""
        summary = self.get_portfolio_summary(prices)

        total_value = 0
        for h in summary["holdings"].values():
            if "market_value" in h and h["market_value"]:
                total_value += h["market_value"]
            elif "current_shares" in h and "current_price" in h and h["current_price"]:
                total_value += h["current_shares"] * h["current_price"]

        if total_value == 0:
            return {}

        allocation = {}
        for symbol, h in summary["holdings"].items():
            value = 0
            if "market_value" in h:
                value = h["market_value"]
            elif "current_shares" in h and "current_price" in h and h["current_price"]:
                value = h["current_shares"] * h["current_price"]

            allocation[symbol] = (value / total_value * 100) if total_value > 0 else 0

        return allocation

    def get_total_market_value(self, prices: Dict[str, float] = None) -> float:
        """获取总市值"""
        summary = self.get_portfolio_summary(prices)
        total = 0

        for h in summary["holdings"].values():
            if "market_value" in h:
                total += h["market_value"]
            elif "current_shares" in h and "current_price" in h and h["current_price"]:
                total += h["current_shares"] * h["current_price"]

        return total

    def get_all_positions(self) -> Dict[str, Dict]:
        """获取所有仓位信息"""
        symbols = set(t.symbol for t in self.transactions if t.symbol)
        positions = {}

        for symbol in symbols:
            basis = self.wheel_calculator.calculate_adjusted_cost_basis(symbol)
            positions[symbol] = {
                "symbol": symbol,
                "shares": basis["current_shares"],
                "adjusted_cost": basis["adjusted_cost"],
                "option_positions": basis.get("option_positions", {})
            }

        return positions
