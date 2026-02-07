"""
Stock Repair 策略 — 预留 stub

Stock Repair 策略：当持仓亏损时，通过 1:2 Call Spread 降低盈亏平衡点。
- 买入 1 份 ATM Call
- 卖出 2 份 OTM Call
- 净成本接近零

实现时：
1. 创建 calculator.py，继承 BaseStrategyCalculator
2. 创建 service.py，实现加载、指标计算
3. 在 strategies/__init__.py 中注册
"""
from services.strategies.base import BaseStrategyCalculator

__all__: list = []

# TODO: 实现 RepairCalculator(BaseStrategyCalculator) 和 RepairService
