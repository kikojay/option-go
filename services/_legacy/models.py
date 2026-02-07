"""
旧交易数据模型 — 向后兼容层

供 OptionCalculator / WheelStrategyCalculator / PortfolioCalculator 使用。
等 Backlog B-1 重写完成后随 _legacy 包一起删除。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    """交易类型"""
    STOCK = "stock"
    OPTION = "option"
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class OptionSubtype(str, Enum):
    """期权交易子类型"""
    SELL_PUT = "sell_put"
    BUY_PUT = "buy_put"
    SELL_CALL = "sell_call"
    BUY_CALL = "buy_call"
    ASSIGNMENT = "assignment"
    CALLED_AWAY = "called_away"


class StockSubtype(str, Enum):
    """股票交易子类型"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Transaction:
    """
    旧版统一交易模型（向后兼容）

    金额约定：
    - amount 正数 = 支出/成本/买入
    - amount 负数 = 收入/收益/卖出
    """
    type: TransactionType
    subtype: Optional[str]
    date: str
    amount: float

    symbol: Optional[str] = None
    account_id: Optional[int] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    fees: float = 0
    category_id: Optional[int] = None
    note: Optional[str] = None

    strike_price: Optional[float] = None
    expiration_date: Optional[str] = None
    option_direction: Optional[int] = None

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = TransactionType(self.type)
