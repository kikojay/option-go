"""
年度汇总 CRUD

每年一条记录，存储税前收入、社保、个税、投资收益等汇总数据。
"""
from typing import Optional, List, Dict, Any

from db.connection import get_connection


def upsert(
    year: int,
    *,
    pre_tax_income: float = 0,
    social_insurance: float = 0,
    income_tax: float = 0,
    investment_income: float = 0,
    note: Optional[str] = None,
) -> None:
    """
    更新或插入年度汇总

    post_tax_income 自动计算：
    = pre_tax_income - social_insurance - income_tax + investment_income
    """
    post_tax = pre_tax_income - social_insurance - income_tax + investment_income

    conn = get_connection()
    conn.execute("""
        INSERT INTO yearly_summary
        (year, pre_tax_income, social_insurance, income_tax,
         post_tax_income, investment_income, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(year) DO UPDATE SET
            pre_tax_income    = excluded.pre_tax_income,
            social_insurance  = excluded.social_insurance,
            income_tax        = excluded.income_tax,
            post_tax_income   = excluded.post_tax_income,
            investment_income = excluded.investment_income,
            note              = excluded.note
    """, (
        year, pre_tax_income, social_insurance, income_tax,
        post_tax, investment_income, note,
    ))
    conn.commit()
    conn.close()


def get_all() -> List[Dict[str, Any]]:
    """获取所有年度汇总（按年份倒序）"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM yearly_summary ORDER BY year DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_year(year: int) -> Optional[Dict[str, Any]]:
    """获取指定年份的汇总"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM yearly_summary WHERE year = ?", (year,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete(year: int) -> bool:
    """删除指定年份的汇总"""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM yearly_summary WHERE year = ?", (year,)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
