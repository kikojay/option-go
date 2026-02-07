"""
策略/周期数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum
from .transaction import Transaction


class CampaignStatus(str, Enum):
    """策略状态"""
    ACTIVE = "active"   # 进行中
    CLOSED = "closed"   # 已关闭
    PAUSED = "paused"   # 已暂停


@dataclass
class Campaign:
    """
    策略周期模型
    
    一个 Campaign 代表一个完整的期权车轮策略周期。
    例如：白银(SLV)的整个卖put-接盘-卖call-被买走的完整周期。
    """
    
    symbol: str                                    # 股票代码（如 AAPL, SLV）
    status: CampaignStatus = CampaignStatus.ACTIVE # 策略状态
    target_shares: int = 100                       # 目标持股数
    
    # 时间范围
    start_date: Optional[str] = None              # 开始日期 YYYY-MM-DD
    end_date: Optional[str] = None                # 结束日期 YYYY-MM-DD
    
    # 关联的交易列表
    transactions: List[Transaction] = field(default_factory=list)
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_transaction(self, transaction: Transaction) -> None:
        """添加交易到策略"""
        self.transactions.append(transaction)
    
    def get_transactions_by_type(self, tx_type: str) -> List[Transaction]:
        """按交易类型筛选"""
        return [t for t in self.transactions if t.type.value == tx_type]
    
    @property
    def is_active(self) -> bool:
        """是否活动"""
        return self.status == CampaignStatus.ACTIVE
    
    @property 
    def is_closed(self) -> bool:
        """是否已关闭"""
        return self.status == CampaignStatus.CLOSED
