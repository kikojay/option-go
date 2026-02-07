"""容错回归测试：空库与异常路径。"""
from __future__ import annotations

import sqlite3

from services import (
    OverviewService,
    SnapshotService,
    YearlyService,
    ExpenseService,
    TradingService,
    PortfolioService,
    WheelService,
)
from db.connection import sync_shadow_from_prod


def test_services_empty_db(empty_db):
    """空库时各服务应返回 None 或空结果。"""
    assert OverviewService.get_trend() is None
    assert SnapshotService.get_trend() is None
    assert SnapshotService.get_detail_rows(usd_rmb=7.0) is None
    assert YearlyService.get_data() is None
    assert ExpenseService.load(usd_rmb=7.0, hkd_rmb=0.9) is None
    assert TradingService.load(usd_rmb=7.0) is None
    assert PortfolioService.load(usd_rmb=7.0) is None
    assert WheelService.load() is None


def test_sync_shadow_from_prod(tmp_path):
    """shadow 同步函数在临时文件上可用。"""
    prod = tmp_path / "prod.db"
    shadow = tmp_path / "shadow.db"

    # 创建临时 prod 数据库
    conn = sqlite3.connect(prod)
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
    conn.commit()
    conn.close()

    out = sync_shadow_from_prod(prod_path=prod, shadow_path=shadow)
    assert out.exists()
    assert out == shadow
