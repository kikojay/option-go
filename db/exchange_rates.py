"""
汇率 CRUD

支持 DB + 文件缓存双写策略（§2.6.1）。
此模块只负责 SQLite 层的 CRUD，API 调用在 api/exchange_rates.py 中。
"""
from typing import Optional, List, Dict, Any
from datetime import date as date_type

from db.connection import get_connection


def upsert(date_str: str, currency: str, rate_to_usd: float, rate_to_rmb: float):
    """
    写入或更新汇率记录（UPSERT）

    利用 UNIQUE(date, currency) 约束，已存在则更新。
    """
    conn = get_connection()
    conn.execute("""
        INSERT INTO exchange_rates (date, currency, rate_to_usd, rate_to_rmb)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date, currency) DO UPDATE SET
            rate_to_usd = excluded.rate_to_usd,
            rate_to_rmb = excluded.rate_to_rmb,
            updated_at  = CURRENT_TIMESTAMP
    """, (date_str, currency, rate_to_usd, rate_to_rmb))
    conn.commit()
    conn.close()


def get_by_date(date_str: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取指定日期的所有币种汇率

    Returns:
        汇率记录列表，如果该日期无记录则返回 None
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM exchange_rates WHERE date = ? ORDER BY currency",
        (date_str,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows] if rows else None


def get_by_date_and_currency(
    date_str: str, currency: str
) -> Optional[Dict[str, Any]]:
    """获取指定日期、指定币种的汇率"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM exchange_rates WHERE date = ? AND currency = ?",
        (date_str, currency),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest() -> Optional[List[Dict[str, Any]]]:
    """
    获取最近一个日期的所有汇率（用于 fallback）

    Returns:
        最新日期的汇率记录列表，无记录则返回 None
    """
    conn = get_connection()
    # 先找最新日期
    latest = conn.execute(
        "SELECT MAX(date) as max_date FROM exchange_rates"
    ).fetchone()
    if not latest or not latest["max_date"]:
        conn.close()
        return None

    rows = conn.execute(
        "SELECT * FROM exchange_rates WHERE date = ? ORDER BY currency",
        (latest["max_date"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows] if rows else None


def get_history(
    currency: str, *, days: int = 30
) -> List[Dict[str, Any]]:
    """
    获取某币种的历史汇率记录

    Args:
        currency: 币种 (USD/HKD/CNY)
        days:     最近 N 天

    Returns:
        按日期倒序的汇率记录列表
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM exchange_rates WHERE currency = ? "
        "ORDER BY date DESC LIMIT ?",
        (currency, days),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
