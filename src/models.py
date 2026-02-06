"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TransactionType(str, Enum):
    STOCK = "stock"
    OPTION = "option"
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class OptionSubtype(str, Enum):
    SELL_PUT = "sell_put"
    BUY_PUT = "buy_put"
    SELL_CALL = "sell_call"
    BUY_CALL = "buy_call"
    ASSIGNMENT = "assignment"  # 被行权接盘
    CALLED_AWAY = "called_away"  # 股票被买走


class StockSubtype(str, Enum):
    BUY = "buy"
    SELL = "sell"


class CampaignStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    PAUSED = "paused"


@dataclass
class Transaction:
    """统一交易模型"""
    type: TransactionType  # stock | option | expense | income | transfer
    subtype: Optional[str]  # buy | sell | sell_put | buy_put | sell_call | buy_call | assignment | called_away
    date: str  # YYYY-MM-DD
    amount: float  # 总金额（正数表示支出/买入，负数表示收入/卖出）
    symbol: Optional[str] = None  # 股票代码
    account_id: Optional[int] = None
    quantity: Optional[int] = None  # 股数
    price: Optional[float] = None  # 单价
    fees: float = 0
    category_id: Optional[int] = None
    note: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Campaign:
    """策略周期"""
    symbol: str
    status: CampaignStatus = CampaignStatus.ACTIVE
    target_shares: int = 100
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    transactions: List[Transaction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Account:
    """账户"""
    name: str
    category_id: int
    balance: float = 0
    currency: str = "USD"
    is_active: bool = True


@dataclass
class AccountCategory:
    """账户分类"""
    name: str
    type: str  # asset | liability | income | expense
    parent_id: Optional[int] = None
