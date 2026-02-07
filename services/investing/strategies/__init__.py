"""
期权策略注册表

支持的策略：
- wheel: 车轮策略 (Wheel Strategy)
- repair: 修复策略 (Stock Repair) — stub，待实现

扩展新策略 3 步：
1. 在 strategies/<name>/ 下创建 calculator.py（继承 BaseStrategyCalculator）
2. 创建 service.py（实现 load / overview / detail）
3. 在本文件 STRATEGY_REGISTRY 注册
"""
from services.investing.strategies.base import BaseStrategyCalculator
from services.investing.strategies.wheel import WheelService, WheelCalculator

# ── 策略注册表 ──
STRATEGY_REGISTRY: dict = {
    "wheel": WheelService,
}


def get_strategy_service(name: str):
    """
    获取策略服务类

    Raises:
        ValueError: 未知策略名
    """
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"未知策略: {name}，可用: {available}")
    return STRATEGY_REGISTRY[name]


__all__ = [
    "BaseStrategyCalculator",
    "WheelService",
    "WheelCalculator",
    "STRATEGY_REGISTRY",
    "get_strategy_service",
]
