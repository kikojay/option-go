"""日常记账相关服务测试。"""
from __future__ import annotations

from services import ExpenseService


def test_expense_service_flow(seeded_db):
    """收支服务的核心统计应可用。"""
    df = ExpenseService.load(usd_rmb=7.0, hkd_rmb=0.9)
    assert df is not None
    year = int(df["year"].max())
    month = df["month"].max()

    ys = ExpenseService.year_summary(df, year)
    assert "income" in ys and "expense" in ys

    ms = ExpenseService.month_summary(df, month)
    assert "net" in ms

    exp_s, inc_s = ExpenseService.category_groups(df, month)
    assert exp_s is not None and inc_s is not None

    detail = ExpenseService.detail(df, month)
    assert "date" in detail.columns
    assert "amount_display" in detail.columns
