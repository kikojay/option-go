"""投资监控相关服务测试。"""
from __future__ import annotations

from services import TradingService, PortfolioService, WheelService


def test_trading_service(seeded_db):
    """交易日志服务应返回汇总与明细。"""
    df = TradingService.load(usd_rmb=7.0)
    assert df is not None

    metrics = TradingService.metrics(df)
    assert "buy" in metrics and "fees" in metrics

    detail = TradingService.detail(df, lambda s: s)
    assert "date" in detail.columns
    assert "amount_rmb" in detail.columns


def test_portfolio_service(seeded_db, monkeypatch):
    """投资组合服务应能加载持仓。"""
    # 避免外部行情依赖
    monkeypatch.setattr(
        "services.investing.portfolio.service.get_batch_prices",
        lambda symbols: {s: {"price": 200.0} for s in symbols},
    )

    data = PortfolioService.load(usd_rmb=7.0)
    assert data is not None
    assert data["holdings"]

    metrics = PortfolioService.calc_overview_metrics(data)
    assert metrics["total_value"] > 0

    trend = PortfolioService.build_trend_data(data)
    assert trend is not None


def test_wheel_service(seeded_db):
    """车轮策略服务应能识别标的。"""
    data = WheelService.load()
    assert data is not None
    assert data["option_symbols"]

    rows = WheelService.overview_rows(
        data["option_symbols"],
        data["all_relevant"],
        data["wheel_calc"],
        lambda s: s,
    )
    assert rows
    assert "symbol" in rows[0]
