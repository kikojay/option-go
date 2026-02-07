"""投资监控页面"""
from .trading import render as page_trading
from .wheel import render as page_wheel
from .portfolio import render as page_portfolio

__all__ = ["page_trading", "page_wheel", "page_portfolio"]
