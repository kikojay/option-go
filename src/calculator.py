"""
盈亏计算模块
"""
from typing import List, Dict, Optional
from datetime import datetime
from src.models import Transaction, Campaign


class WheelCalculator:
    """车轮策略计算器"""

    def __init__(self, transactions: List[Transaction]):
        self.transactions = sorted(transactions, key=lambda x: x.date)
        self._cache = {}

    def calculate_option_positions(self, symbol: str) -> Dict:
        """
        计算期权仓位
        返回: {put: 张数, call: 张数}
        正数=多头(+1), 负数=空头(-1)
        """
        tx = [t for t in self.transactions if t.symbol == symbol and t.type == "option"]

        put_qty = 0
        call_qty = 0

        for t in tx:
            direction = t.option_direction if t.option_direction else (1 if t.subtype.startswith("buy") else -1)
            if "put" in t.subtype:
                put_qty += direction * (t.quantity or 0)
            elif "call" in t.subtype:
                call_qty += direction * (t.quantity or 0)

        return {
            "put": put_qty,
            "call": call_qty,
            "put_direction": 1 if put_qty >= 0 else -1,
            "call_direction": 1 if call_qty >= 0 else -1
        }

    def calculate_option_pnl(self, symbol: str) -> Dict:
        """
        计算期权盈亏
        - Sell Put @1: 收 $100, 仓位 -1, P&L = +$100
        - Buy Put @1:  支 $100, 仓位 +1, P&L = -$100
        """
        tx = [t for t in self.transactions if t.symbol == symbol and t.type == "option"]

        total_pnl = 0

        for t in tx:
            # amount 是负数（收入），取反为正数（盈利）
            pnl = -t.amount
            total_pnl += pnl

        return {"total_pnl": total_pnl}

    def calculate_adjusted_cost_basis(self, symbol: str) -> Dict:
        """
        计算调整后成本基准
        公式：(股票买入成本 + 权利金收入 + 手续费) / 持仓数量
        """
        tx = [t for t in self.transactions if t.symbol == symbol]

        # 股票买入成本（负数，支出）
        stock_buy = sum(
            t.amount for t in tx
            if t.type == "stock" and t.subtype in ["buy", "assignment"]
        )

        # 卖出股票收入（正数）
        stock_sell = sum(
            t.amount for t in tx
            if t.type == "stock" and t.subtype in ["sell", "called_away"]
        )

        # 收取的权利金（负数，表示收入）
        premiums_collected = sum(
            t.amount for t in tx
            if t.subtype in ["sell_put", "sell_call"]
        )

        # 手续费支出（正数）
        fees_paid = sum(t.fees for t in tx)

        # 当前持仓
        shares_bought = sum(
            t.quantity or 0 for t in tx
            if t.type == "stock" and t.subtype in ["buy", "assignment"]
        )
        shares_sold = sum(
            t.quantity or 0 for t in tx
            if t.type == "stock" and t.subtype in ["sell", "called_away"]
        )
        current_shares = shares_bought - shares_sold

        if current_shares <= 0:
            return {
                "current_shares": 0,
                "adjusted_cost": 0,
                "total_premiums": premiums_collected,
                "cost_basis": 0,
                "option_positions": self.calculate_option_positions(symbol)
            }

        # 调整后成本（每股）
        net_cost = -stock_buy + premiums_collected + fees_paid
        adjusted_cost = net_cost / current_shares

        return {
            "current_shares": current_shares,
            "adjusted_cost": adjusted_cost,
            "total_premiums": premiums_collected,
            "cost_basis": net_cost,
            "premiums_per_share": -premiums_collected / current_shares,
            "fees_per_share": fees_paid / current_shares,
            "option_positions": self.calculate_option_positions(symbol)
        }

    def calculate_realized_pnl(self, symbol: str = None) -> float:
        """计算已实现盈亏"""
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]

        # 期权盈亏（收入为正）
        option_pnl = sum(
            -t.amount for t in tx
            if t.type == "option"
        )

        # 股票买卖盈亏
        stock_pnl = sum(
            (-t.amount) for t in tx
            if t.type == "stock" and t.subtype in ["sell", "called_away"]
        ) + sum(
            t.amount for t in tx
            if t.type == "stock" and t.subtype in ["buy", "assignment"]
        )

        # 手续费
        fees = sum(t.fees for t in tx)

        return option_pnl + stock_pnl - fees

    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> Dict:
        """计算未实现盈亏（浮动盈亏）"""
        basis = self.calculate_adjusted_cost_basis(symbol)

        if basis["current_shares"] <= 0:
            return {
                "unrealized_pnl": 0,
                "current_shares": 0,
                "option_positions": basis.get("option_positions", {})
            }

        market_value = basis["current_shares"] * current_price
        unrealized_pnl = market_value - basis["cost_basis"]

        return {
            "unrealized_pnl": unrealized_pnl,
            "market_value": market_value,
            "current_shares": basis["current_shares"],
            "adjusted_cost": basis["adjusted_cost"],
            "option_positions": basis.get("option_positions", {})
        }

    def calculate_campaign_summary(self, symbol: str, current_price: float = None) -> Dict:
        """计算 Campaign 汇总"""
        basis = self.calculate_adjusted_cost_basis(symbol)
        realized = self.calculate_realized_pnl(symbol)
        option_pnl = self.calculate_option_pnl(symbol)

        unrealized = 0
        if current_price:
            unrealized_data = self.calculate_unrealized_pnl(symbol, current_price)
            unrealized = unrealized_data["unrealized_pnl"]

        return {
            "symbol": symbol,
            "current_shares": basis["current_shares"],
            "adjusted_cost": basis["adjusted_cost"],
            "total_premiums": basis["total_premiums"],
            "realized_pnl": realized,
            "option_pnl": option_pnl["total_pnl"],
            "unrealized_pnl": unrealized,
            "total_pnl": realized + unrealized,
            "current_price": current_price,
            "option_positions": basis.get("option_positions", {})
        }

    def calculate_breakeven_weeks(self, symbol: str, avg_weekly_premium: float, target_cost: float = 0) -> Dict:
        """计算回本所需周数"""
        basis = self.calculate_adjusted_cost_basis(symbol)

        if avg_weekly_premium <= 0:
            return {"weeks": None, "message": "权利金必须大于0"}

        current_cost = basis["adjusted_cost"]
        weeks_needed = (current_cost - target_cost) / avg_weekly_premium

        return {
            "weeks": round(weeks_needed, 1),
            "current_cost": current_cost,
            "target_cost": target_cost,
            "avg_weekly_premium": avg_weekly_premium,
            "message": f"以每周 ${avg_weekly_premium:.2f} 权利金计算，还需 {weeks_needed:.1f} 周回本"
        }

    def get_transaction_history(self, symbol: str = None) -> List[Dict]:
        """获取交易历史"""
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]

        return [
            {
                "date": t.date,
                "type": t.type,
                "subtype": t.subtype,
                "symbol": t.symbol,
                "quantity": t.quantity,
                "price": t.price,
                "amount": t.amount,
                "note": t.note
            }
            for t in tx
        ]


class PortfolioCalculator:
    """组合计算器"""

    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions
        self.wheel_calculator = WheelCalculator(transactions)

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
            total_realized += summary["realized_pnl"]
            total_unrealized += summary["unrealized_pnl"]

        return {
            "holdings": holdings,
            "total_realized_pnl": total_realized,
            "total_unrealized_pnl": total_unrealized,
            "total_pnl": total_realized + total_unrealized
        }

    def get_asset_allocation(self) -> Dict[str, float]:
        """资产配置"""
        summary = self.get_portfolio_summary()
        total = sum(h["market_value"] if "market_value" in h else 0 for h in summary["holdings"].values())

        if total == 0:
            return {}

        return {
            symbol: (h.get("market_value", 0) / total * 100)
            for symbol, h in summary["holdings"].items()
        }
