"""资产追踪页面"""
from .overview import render as page_overview
from .snapshots import render as page_snapshots
from .yearly import render as page_yearly

__all__ = ["page_overview", "page_snapshots", "page_yearly"]
