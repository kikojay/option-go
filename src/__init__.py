"""
Option Wheel Tracker - 期权车轮策略跟踪系统

向后兼容层 - 保持旧代码的导入路径继续工作

这个文件的目的是在过渡期间提供向后兼容性。
新代码应该直接从各个模块导入，而不是从这里导入。
"""

# 导出所有模型（从新位置）
from .models import (
    Transaction,
    TransactionType,
    OptionSubtype,
    StockSubtype,
    Campaign,
    CampaignStatus,
    Account,
    AccountCategory,
)

# 导出期权计算（从新位置）
from .options import (
    OptionCalculator,
    WheelStrategyCalculator as WheelCalculator,
)

# 导出组合计算（从新位置）
from .portfolio import (
    PortfolioCalculator,
    PortfolioAnalyzer,
)

# 可视化模块可选导入（依需而定）
# 如果需要，在使用时动态导入：
# from src.visualization import PortfolioDashboard

__all__ = [
    # 模型
    'Transaction',
    'TransactionType',
    'OptionSubtype',
    'StockSubtype',
    'Campaign',
    'CampaignStatus',
    'Account',
    'AccountCategory',
    # 计算
    'WheelCalculator',
    'OptionCalculator',
    'PortfolioCalculator',
    'PortfolioAnalyzer',
]
