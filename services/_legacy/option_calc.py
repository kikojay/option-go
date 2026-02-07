"""
期权计算模块 — 处理期权的盈亏和仓位计算
"""
from typing import List, Dict
from services._legacy.models import Transaction


class OptionCalculator:
    """期权计算器 — 专注于期权相关的盈亏和仓位计算"""

    def __init__(self, transactions: List[Transaction]):
        """
        初始化期权计算器

        Args:
            transactions: 交易列表
        """
        self.transactions = sorted(transactions, key=lambda x: x.date)

    def calculate_option_positions(self, symbol: str) -> Dict:
        """
        计算特定股票的期权仓位

        Returns:
            {"put": 张数, "call": 张数, "put_direction": 1/-1, "call_direction": 1/-1}
        """
        tx = [t for t in self.transactions
              if t.symbol == symbol and t.type.value == "option"]

        put_qty = 0
        call_qty = 0

        for t in tx:
            direction = t.option_direction if t.option_direction else \
                       (1 if t.subtype.startswith("buy") else -1)

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
        计算期权盈亏（不含股票盈亏）

        Returns:
            {"total_pnl": 金额}
        """
        tx = [t for t in self.transactions
              if t.symbol == symbol and t.type.value == "option"]

        total_pnl = sum(-t.amount for t in tx)
        return {"total_pnl": total_pnl}

    def get_open_positions(self, symbol: str) -> List[Dict]:
        """获取特定股票的未平仓期权头寸"""
        tx = [t for t in self.transactions
              if t.symbol == symbol and t.type.value == "option"]

        positions = {}
        for t in tx:
            key = (t.strike_price, t.expiration_date, t.subtype)
            if key not in positions:
                positions[key] = {
                    "strike": t.strike_price,
                    "expiration": t.expiration_date,
                    "subtype": t.subtype,
                    "quantity": 0,
                    "avg_price": 0,
                    "total_cost": 0,
                }
            pos = positions[key]
            pos["quantity"] += (t.quantity or 0) * (1 if "buy" in t.subtype else -1)
            pos["total_cost"] += t.amount
            if pos["quantity"] != 0:
                pos["avg_price"] = abs(pos["total_cost"] / pos["quantity"])

        return [p for p in positions.values() if p["quantity"] != 0]

    def get_premiums_summary(self, symbol: str = None) -> Dict:
        """
        获取权利金汇总

        Returns:
            {"total_collected": 总收入, "total_paid": 总支出, "net_premium": 净权利金}
        """
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]

        tx = [t for t in tx if t.type.value == "option"]

        collected = sum(-t.amount for t in tx if t.amount < 0)
        paid = sum(t.amount for t in tx if t.amount > 0)

        return {
            "total_collected": collected,
            "total_paid": paid,
            "net_premium": collected - paid
        }
