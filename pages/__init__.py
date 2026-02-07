"""
pages 包 — 按业务域组织的视图层

每个页面只做：路由 → 读 session_state → 调 Service → 调 UI 渲染
不直接碰 DB / FinanceEngine。
"""
from .assets import page_overview, page_snapshots, page_yearly
from .accounting import page_expense
from .investing import page_trading, page_wheel, page_portfolio
from .settings import render as page_settings

__all__ = [
    "page_overview",
    "page_snapshots",
    "page_yearly",
    "page_expense",
    "page_trading",
    "page_wheel",
    "page_settings",
    "page_portfolio",
]
