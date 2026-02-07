"""
账户数据模型
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class AccountCategoryType(str, Enum):
    """账户分类类型"""
    ASSET = "asset"           # 资产
    LIABILITY = "liability"   # 负债
    INCOME = "income"         # 收入
    EXPENSE = "expense"       # 支出


@dataclass
class AccountCategory:
    """
    账户分类模型
    
    用于对账户进行层级分类。
    例如：资产 > 投资账户 > 券商账户
    """
    
    name: str                              # 分类名称
    type: AccountCategoryType              # 分类类型
    parent_id: Optional[int] = None        # 父分类ID（支持层级）
    
    def __post_init__(self):
        """数据验证"""
        if isinstance(self.type, str):
            self.type = AccountCategoryType(self.type)


@dataclass
class Account:
    """
    账户模型
    
    代表一个独立的投资或财务账户。
    例如：Interactive Brokers 账户、银行储蓄账户等。
    """
    
    name: str                                  # 账户名称
    category_id: int                         # 所属分类ID
    
    balance: float = 0                       # 账户余额
    currency: str = "USD"                    # 货币
    is_active: bool = True                   # 是否活跃
    
    @property
    def is_investment_account(self) -> bool:
        """是否为投资账户"""
        return "broker" in self.name.lower() or "investment" in self.name.lower()
