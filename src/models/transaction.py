"""
交易数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    """交易类型"""
    STOCK = "stock"       # 股票交易
    OPTION = "option"     # 期权交易
    EXPENSE = "expense"   # 支出
    INCOME = "income"     # 收入
    TRANSFER = "transfer" # 转账


class OptionSubtype(str, Enum):
    """期权交易子类型"""
    SELL_PUT = "sell_put"      # 卖看跌期权
    BUY_PUT = "buy_put"        # 买看跌期权
    SELL_CALL = "sell_call"    # 卖看涨期权
    BUY_CALL = "buy_call"      # 买看涨期权
    ASSIGNMENT = "assignment"   # 被行权接盘
    CALLED_AWAY = "called_away" # 股票被买走


class StockSubtype(str, Enum):
    """股票交易子类型"""
    BUY = "buy"   # 买入
    SELL = "sell" # 卖出


@dataclass
class Transaction:
    """
    统一交易模型
    
    金额约定：
    - amount 正数 = 支出/成本/买入
    - amount 负数 = 收入/收益/卖出
    
    示例：
    - 买入100股@100: amount=10000, quantity=100
    - 卖出100股@110: amount=-11000, quantity=100
    - 卖put权利金: amount=-100
    - 买put权利金: amount=50
    """
    
    type: TransactionType           # stock | option | expense | income | transfer
    subtype: Optional[str]          # buy | sell | sell_put | buy_put | sell_call | buy_call | assignment | called_away
    date: str                       # YYYY-MM-DD
    amount: float                   # 金额（正=支出，负=收入）
    
    # 可选字段
    symbol: Optional[str] = None         # 股票代码（如 AAPL, SLV）
    account_id: Optional[int] = None     # 账户ID
    quantity: Optional[int] = None       # 股数或期权张数
    price: Optional[float] = None        # 单价（股票单价或期权权利金）
    fees: float = 0                      # 手续费
    category_id: Optional[int] = None    # 分类ID
    note: Optional[str] = None           # 备注
    
    # 期权特定字段
    strike_price: Optional[float] = None # 行权价
    expiration_date: Optional[str] = None # 到期日 YYYY-MM-DD
    option_direction: Optional[int] = None # 期权方向：+1=多头, -1=空头
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """数据验证"""
        if isinstance(self.type, str):
            self.type = TransactionType(self.type)
