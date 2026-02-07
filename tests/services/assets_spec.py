"""资产追踪相关服务测试。"""
from __future__ import annotations

from services import OverviewService, SnapshotService, YearlyService


def test_overview_metrics(seeded_db):
    """总览指标应包含资产数据。"""
    data = OverviewService.get_metrics(usd_rmb=7.0, hkd_rmb=0.9)
    assert data["total_rmb"] > 0
    assert data["total_usd"] >= 0
    assert data["cat_breakdown"]
    for item in data["cat_breakdown"]:
        assert "cat" in item and "value" in item and "color" in item


def test_overview_trend(seeded_db):
    """趋势数据应返回 DataFrame。"""
    trend = OverviewService.get_trend()
    assert trend is not None
    assert "date" in trend.columns
    assert "asset_wan" in trend.columns


def test_snapshot_service(seeded_db):
    """快照汇总与明细可读取。"""
    summary = SnapshotService.get_summary(usd_rmb=7.0, hkd_rmb=0.9)
    assert summary["accounts"]

    trend = SnapshotService.get_trend()
    assert trend is not None
    assert "date_label" in trend.columns

    detail = SnapshotService.get_detail_rows(usd_rmb=7.0)
    assert detail is not None
    assert "date" in detail.columns


def test_yearly_service(seeded_db):
    """年度汇总可加载并计算累计。"""
    df = YearlyService.get_data()
    assert df is not None
    totals = YearlyService.totals(df)
    assert totals["pre_tax"] > 0
