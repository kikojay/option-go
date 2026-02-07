"""
业务逻辑层 — 按业务域隔离

目录结构：
- services/assets/        资产追踪（总览/快照/年度）
- services/accounting/    日常记账（收支）
- services/investing/     投资监控（交易/组合/策略）
- services/_legacy/       旧版计算器兼容层（Backlog B-1 后删除）

架构规则：
- services/ → db/ + api/ + config/ + utils/（可以调用）
- 绝对禁止：services/ → ui/、services/ → pages/
"""
from services.assets import OverviewService, SnapshotService, YearlyService
from services.accounting import ExpenseService
from services.investing import TradingService, PortfolioService, WheelService

__all__ = [
    "OverviewService",
    "SnapshotService",
    "ExpenseService",
    "TradingService",
    "YearlyService",
    "PortfolioService",
    "WheelService",
]
