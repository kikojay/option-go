"""
services 内部辅助函数 — 不暴露给前端

仅包含跨多个 Service 共用的通用工具函数。
策略特定的计算逻辑（cost_timeline / weeks_to_zero 等）
已下沉到 strategies/<name>/calculator.py。
"""
from __future__ import annotations

from typing import Tuple


def cumulative_deposits(flows: list) -> list:
    """从入金/出金记录计算累计净入金序列"""
    records, running = [], 0.0
    for cf in sorted(flows, key=lambda x: x["datetime"]):
        act = cf.get("action", "")
        amt = cf.get("price", 0)
        if act == "DEPOSIT":
            running += amt
        elif act == "WITHDRAW":
            running -= amt
        records.append({"date": cf["datetime"][:10], "deposit": running})
    return records


def estimate_deposits(tx_raw: list) -> list:
    """无显式入金记录时，从买入交易估算累计投入"""
    records, running = [], 0.0
    for t in sorted(tx_raw, key=lambda x: x["datetime"]):
        if t.get("action") in ("BUY", "ASSIGNMENT"):
            running += (t.get("price") or 0) * (t.get("quantity") or 0)
        records.append({"date": t["datetime"][:10], "deposit": running})
    return records


def estimate_dividends(sym: str, shares: int) -> Tuple[float, float]:
    """估算年度分红和月分红（使用 yfinance，失败时返回 0）"""
    annual = 0.0
    try:
        import yfinance as yf
        info = yf.Ticker(sym).info
        annual = (info.get("dividendRate", 0) or 0) * shares
    except Exception:
        pass
    return annual, annual / 12
