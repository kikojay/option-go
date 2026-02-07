"""前端模块 - 所有页面和配置"""
from .page_overview import page_overview
from .page_snapshots import page_snapshots
from .page_yearly import page_yearly_summary
from .page_expense import page_expense_tracker
from .page_portfolio import page_portfolio
from .page_trading_log import page_trading_log
from .page_wheel import page_wheel
from .page_settings import page_settings

__all__ = [
    "page_overview",
    "page_snapshots",
    "page_yearly_summary",
    "page_expense_tracker",
    "page_portfolio",
    "page_trading_log",
    "page_wheel",
    "page_settings",
]
