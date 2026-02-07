"""测试夹具：重建数据库并插入最小可用数据。"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import os
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 测试环境固定使用 shadow DB
os.environ.setdefault("WEALTH_DB_ROLE", "shadow")

# 提供最小 streamlit stub，确保 @st.cache_data 可用
if "streamlit" not in sys.modules:
    st_stub = types.SimpleNamespace()

    def _decorator(fn):
        def _wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        _wrapped.clear = lambda: None
        return _wrapped

    def _cache_factory(*_args, **_kwargs):
        return _decorator

    st_stub.cache_data = _cache_factory
    st_stub.cache_resource = _cache_factory
    st_stub.session_state = {}
    sys.modules["streamlit"] = st_stub

# 提供最小 plotly.graph_objects stub，避免导入失败
if "plotly" not in sys.modules:
    plotly_stub = types.ModuleType("plotly")
    graph_objects_stub = types.ModuleType("plotly.graph_objects")

    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

    graph_objects_stub.Figure = _Dummy
    graph_objects_stub.Pie = _Dummy
    graph_objects_stub.Scatter = _Dummy
    graph_objects_stub.Bar = _Dummy
    graph_objects_stub.Heatmap = _Dummy

    plotly_stub.graph_objects = graph_objects_stub
    sys.modules["plotly"] = plotly_stub
    sys.modules["plotly.graph_objects"] = graph_objects_stub

# 提供最小 streamlit_extras stub
if "streamlit_extras" not in sys.modules:
    extras_stub = types.ModuleType("streamlit_extras")
    metric_cards_stub = types.ModuleType("streamlit_extras.metric_cards")
    stylable_container_stub = types.ModuleType("streamlit_extras.stylable_container")

    def _style_metric_cards(**_kwargs):
        return None

    class _Stylable:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    metric_cards_stub.style_metric_cards = _style_metric_cards
    stylable_container_stub.stylable_container = _Stylable

    extras_stub.metric_cards = metric_cards_stub
    extras_stub.stylable_container = stylable_container_stub
    sys.modules["streamlit_extras"] = extras_stub
    sys.modules["streamlit_extras.metric_cards"] = metric_cards_stub
    sys.modules["streamlit_extras.stylable_container"] = stylable_container_stub

import db
from db.connection import get_db_path, init_database, sync_shadow_from_prod


def _reset_db() -> None:
    """删除旧数据库并重建 Schema。"""
    db_path = get_db_path()
    if db_path.exists():
        db_path.unlink()
    init_database()


def _sync_shadow() -> None:
    """将 prod 数据复制到 shadow（按需使用）。"""
    try:
        sync_shadow_from_prod()
    except FileNotFoundError:
        pass


def _seed_accounts() -> None:
    """设置默认账户余额。"""
    conn = db.connection.get_connection()
    cur = conn.cursor()
    balances = [
        ("现金", 10000),
        ("美股", 25000),
        ("A股", 8000),
        ("港股", 5000),
        ("ETF", 12000),
        ("公积金", 30000),
    ]
    for name, balance in balances:
        cur.execute(
            "UPDATE accounts SET balance = ? WHERE name = ?",
            (balance, name),
        )
    conn.commit()
    conn.close()


def _seed_transactions() -> None:
    """插入必要的交易数据。"""
    # 记账
    db.transactions.add("2026-01-05", "INCOME", price=20000, currency="CNY", subcategory="工资")
    db.transactions.add("2026-01-08", "EXPENSE", price=3000, currency="CNY", subcategory="房租")

    # 入金/出金
    db.transactions.add("2026-01-10", "DEPOSIT", quantity=1, price=5000, currency="USD", note="入金")
    db.transactions.add("2026-02-01", "WITHDRAW", quantity=1, price=1000, currency="USD", note="出金")

    # 股票交易
    db.transactions.add("2026-01-12", "BUY", symbol="AAPL", quantity=100, price=180.0, fees=1.0, currency="USD")
    db.transactions.add("2026-02-01", "SELL", symbol="AAPL", quantity=50, price=190.0, fees=1.0, currency="USD")

    # 期权交易
    db.transactions.add("2026-02-03", "STO_CALL", symbol="AAPL", quantity=1, price=2.5, fees=0.65, currency="USD")
    db.transactions.add("2026-02-10", "BTC", symbol="AAPL", quantity=1, price=1.2, fees=0.65, currency="USD")

    # 分红
    db.transactions.add("2026-02-05", "DIVIDEND", symbol="AAPL", quantity=1, price=100.0, currency="USD")


def _seed_snapshots() -> None:
    """插入月度快照。"""
    db.snapshots.create(
        date_str="2026-01-01",
        total_assets_usd=50000,
        total_assets_rmb=360000,
        assets_data={"accounts": []},
        note="1月快照",
    )
    db.snapshots.create(
        date_str="2026-02-01",
        total_assets_usd=52000,
        total_assets_rmb=375000,
        assets_data={"accounts": []},
        note="2月快照",
    )


def _seed_yearly() -> None:
    """插入年度汇总。"""
    db.yearly.upsert(2025, pre_tax_income=300000, social_insurance=50000, income_tax=30000, investment_income=10000)
    db.yearly.upsert(2026, pre_tax_income=320000, social_insurance=52000, income_tax=32000, investment_income=12000)


@pytest.fixture(scope="function")
def seeded_db() -> Iterable[None]:
    """重建数据库并插入测试数据。"""
    _reset_db()
    _seed_accounts()
    _seed_transactions()
    _seed_snapshots()
    _seed_yearly()
    yield


@pytest.fixture(scope="function")
def empty_db() -> Iterable[None]:
    """重建空数据库（只含默认账户）。"""
    _reset_db()
    yield
