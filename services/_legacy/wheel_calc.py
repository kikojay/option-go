"""
车轮策略计算模块 — 专门为期权车轮策略设计
"""
from typing import List, Dict
from services._legacy.models import Transaction
from services._legacy.option_calc import OptionCalculator


class WheelStrategyCalculator:
    """
    车轮策略计算器

    车轮策略(Wheel Strategy)步骤：
    1. 卖出看跌期权 (Sell Put) - 收集权利金，准备接盘
    2. 被行权接盘 (Assignment) - 以行权价买入100股
    3. 卖出看涨期权 (Sell Call) - 在持仓期间继续收集权利金
    4. 被行权买走 (Called Away) - 以行权价卖出100股

    完整循环回到步骤1。
    """

    def __init__(self, transactions: List[Transaction]):
        """
        初始化车轮策略计算器

        Args:
            transactions: 交易列表
        """
        self.transactions = sorted(transactions, key=lambda x: x.date)
        self.option_calc = OptionCalculator(transactions)

    def calculate_adjusted_cost_basis(self, symbol: str) -> Dict:
        """
        计算调整后成本基准（车轮策略的核心）

        公式：(股票买入成本 - 权利金收入 + 手续费) / 持仓数量
        """
        tx = [t for t in self.transactions if t.symbol == symbol]

        stock_buy = sum(
            t.amount for t in tx
            if t.type.value == "stock" and t.subtype in ["buy", "assignment"]
        )

        premiums_from_options = sum(
            t.amount for t in tx
            if t.type.value == "option"
        )

        fees_paid = sum(t.fees for t in tx)

        shares_bought = sum(
            t.quantity or 0 for t in tx
            if t.type.value == "stock" and t.subtype in ["buy", "assignment"]
        )
        shares_sold = sum(
            t.quantity or 0 for t in tx
            if t.type.value == "stock" and t.subtype in ["sell", "called_away"]
        )
        current_shares = shares_bought - shares_sold

        if current_shares <= 0:
            return {
                "current_shares": 0,
                "adjusted_cost": 0,
                "total_premiums": premiums_from_options,
                "cost_basis": 0,
                "option_positions": self.option_calc.calculate_option_positions(symbol)
            }

        net_cost = stock_buy + premiums_from_options + fees_paid
        adjusted_cost = net_cost / current_shares

        return {
            "current_shares": current_shares,
            "adjusted_cost": adjusted_cost,
            "total_premiums": premiums_from_options,
            "cost_basis": net_cost,
            "premiums_per_share": -premiums_from_options / current_shares,
            "fees_per_share": fees_paid / current_shares,
            "option_positions": self.option_calc.calculate_option_positions(symbol)
        }

    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> Dict:
        """计算未实现盈亏（浮动盈亏）"""
        basis = self.calculate_adjusted_cost_basis(symbol)

        if basis["current_shares"] <= 0:
            return {
                "unrealized_pnl": 0,
                "current_shares": 0,
                "market_value": 0,
                "option_positions": basis.get("option_positions", {})
            }

        market_value = basis["current_shares"] * current_price
        unrealized_pnl = market_value - basis["cost_basis"]

        return {
            "unrealized_pnl": unrealized_pnl,
            "market_value": market_value,
            "current_shares": basis["current_shares"],
            "adjusted_cost": basis["adjusted_cost"],
            "cost_basis": basis["cost_basis"],
            "option_positions": basis.get("option_positions", {})
        }

    def calculate_realized_pnl(self, symbol: str = None) -> float:
        """计算已实现盈亏"""
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]

        option_pnl = sum(
            -t.amount for t in tx
            if t.type.value == "option"
        )

        stock_sale_proceeds = sum(
            -t.amount for t in tx
            if t.type.value == "stock" and t.subtype in ["sell", "called_away"]
        )

        stock_purchase_cost = sum(
            t.amount for t in tx
            if t.type.value == "stock" and t.subtype in ["buy", "assignment"]
        )

        fees = sum(t.fees for t in tx)

        stock_pnl = stock_sale_proceeds - stock_purchase_cost
        realized_pnl = stock_pnl + option_pnl - fees

        return realized_pnl

    def calculate_campaign_summary(self, symbol: str, current_price: float = None) -> Dict:
        """计算车轮策略周期的完整汇总"""
        basis = self.calculate_adjusted_cost_basis(symbol)
        option_pnl = self.option_calc.calculate_option_pnl(symbol)

        unrealized = 0
        if current_price:
            unrealized_data = self.calculate_unrealized_pnl(symbol, current_price)
            unrealized = unrealized_data["unrealized_pnl"]

        return {
            "symbol": symbol,
            "current_shares": basis["current_shares"],
            "adjusted_cost": basis["adjusted_cost"],
            "cost_basis": basis["cost_basis"],
            "total_premiums": basis["total_premiums"],
            "option_pnl": option_pnl["total_pnl"],
            "unrealized_pnl": unrealized,
            "total_pnl": option_pnl["total_pnl"] + unrealized,
            "current_price": current_price,
            "option_positions": basis.get("option_positions", {})
        }

    def calculate_breakeven_weeks(self, symbol: str, avg_weekly_premium: float,
                                 target_cost: float = 0) -> Dict:
        """计算回本所需的周数"""
        basis = self.calculate_adjusted_cost_basis(symbol)

        if avg_weekly_premium <= 0:
            return {
                "weeks": None,
                "message": "权利金必须大于0"
            }

        current_cost = basis["adjusted_cost"]
        weeks_needed = (current_cost - target_cost) / avg_weekly_premium

        return {
            "weeks": round(weeks_needed, 1),
            "current_cost": current_cost,
            "target_cost": target_cost,
            "avg_weekly_premium": avg_weekly_premium,
            "message": f"以每周 ${avg_weekly_premium:.2f} 权利金计算，还需 {weeks_needed:.1f} 周回本"
        }

    def get_wheel_cycle_info(self, symbol: str) -> Dict:
        """获取当前车轮周期的详细信息"""
        tx = sorted(
            [t for t in self.transactions if t.symbol == symbol],
            key=lambda x: x.date
        )

        if not tx:
            return {"status": "empty", "message": "无交易"}

        stock_position = 0
        last_action = None

        for t in tx:
            if t.type.value == "stock":
                if t.subtype in ["buy", "assignment"]:
                    stock_position += t.quantity or 0
                    last_action = f"接盘于 {t.date} @ {t.price}"
                elif t.subtype in ["sell", "called_away"]:
                    stock_position -= t.quantity or 0
                    last_action = f"被买走于 {t.date} @ {t.price}"

        if stock_position > 0:
            return {
                "status": "holding",
                "shares": stock_position,
                "message": f"持有 {stock_position} 股，{last_action}"
            }
        else:
            return {
                "status": "waiting",
                "message": "等待下一次接盘机会"
            }
