"""
期权计算模块 - 处理期权的盈亏和仓位计算
"""
from typing import List, Dict
from src.models import Transaction


class OptionCalculator:
    """期权计算器 - 专注于期权相关的盈亏和仓位计算"""

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
        
        Args:
            symbol: 股票代码
            
        Returns:
            {
                "put": 张数,
                "call": 张数,
                "put_direction": 1/-1,
                "call_direction": 1/-1
            }
            
        说明：
        - 正数 = 多头（持有）
        - 负数 = 空头（卖出）
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
        
        Args:
            symbol: 股票代码
            
        Returns:
            {"total_pnl": 金额}
            
        说明：
        - Sell Put @100，收入100 (amount = -100), pnl = +100 ✓
        - Buy Put @50，支出50 (amount = 50), pnl = -50 ✓
        - 新平仓交易也包含在内（所有期权交易的 amount 都算）
        """
        tx = [t for t in self.transactions 
              if t.symbol == symbol and t.type.value == "option"]

        # 直接求和所有期权交易的收支
        # 取反得到盈亏：支出为负P&L，收入为正P&L
        total_pnl = sum(-t.amount for t in tx)

        return {"total_pnl": total_pnl}

    def get_open_positions(self, symbol: str) -> List[Dict]:
        """
        获取特定股票的未平仓期权头寸
        
        Args:
            symbol: 股票代码
            
        Returns:
            未平仓的期权头寸列表
        """
        tx = [t for t in self.transactions 
              if t.symbol == symbol and t.type.value == "option"]
        
        # 按行权价和到期日分组
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
        
        Args:
            symbol: 股票代码（可选，为None时汇总所有）
            
        Returns:
            {
                "total_collected": 总收入,
                "total_paid": 总支出,
                "net_premium": 净权利金
            }
        """
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]
        
        tx = [t for t in tx if t.type.value == "option"]
        
        collected = sum(-t.amount for t in tx if t.amount < 0)  # 收入取正
        paid = sum(t.amount for t in tx if t.amount > 0)        # 支出取正
        
        return {
            "total_collected": collected,
            "total_paid": paid,
            "net_premium": collected - paid
        }
