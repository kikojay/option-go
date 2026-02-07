"""
旧版计算器兼容层（Strategy A — 原样搬运）

包含 Phase 1-7 验证通过的计算逻辑，原样保留旧 Transaction 模型。
等后续 Backlog B-1 重写为 DataFrame-native 后，此包将被删除。

导出：
- Transaction, TransactionType          旧数据模型
- OptionCalculator                      期权计算器
- WheelStrategyCalculator               车轮策略计算器
- PortfolioCalculator                   投资组合计算器
- dict_to_transaction                   dict → 旧 Transaction 转换
"""
from services._legacy.models import Transaction, TransactionType
from services._legacy.option_calc import OptionCalculator
from services._legacy.wheel_calc import WheelStrategyCalculator
from services._legacy.portfolio_calc import PortfolioCalculator
from services._legacy.converters import dict_to_transaction

__all__ = [
    "Transaction",
    "TransactionType",
    "OptionCalculator",
    "WheelStrategyCalculator",
    "PortfolioCalculator",
    "dict_to_transaction",
]
