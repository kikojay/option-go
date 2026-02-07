"""页面：投资组合 Portfolio"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.database_v2 import get_transactions
from src import PortfolioCalculator

from .config import COLORS
from .helpers import (
    fetch_exchange_rates, dict_to_transaction,
    plotly_layout, metric_row, stock_label,
)


def page_portfolio():
    st.title("📈 投资组合 Portfolio")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_rmb:.2f} CNY")

    tx_raw = get_transactions(category="投资", limit=500)
    if not tx_raw:
        st.info("暂无投资数据，去 📝 交易日志 添加吧")
        return

    transactions = [dict_to_transaction(t) for t in tx_raw]
    calc = PortfolioCalculator(transactions)
    summary = calc.get_portfolio_summary()
    holdings = summary.get("holdings", {})

    if not holdings:
        st.info("暂无持仓")
        return

    total_value = sum(
        h.get("market_value", 0) or h.get("cost_basis", 0)
        for h in holdings.values()
    )
    total_cost = sum(h.get("cost_basis", 0) for h in holdings.values())
    total_pnl = summary["total_unrealized_pnl"]

    metric_row([
        ("💵 总市值 (USD)", f"${total_value:,.2f}"),
        ("💴 折合人民币",   f"¥{total_value * usd_rmb:,.2f}"),
        ("📊 浮动盈亏",     f"${total_pnl:,.2f}", f"${total_pnl:,.2f}"),
    ])

    # ── 图表 ──
    symbols = list(holdings.keys())
    left, right = st.columns(2)

    with left:
        st.subheader("📊 市值分布")
        vals = [
            h.get("market_value", 0) or h.get("cost_basis", 0)
            for h in holdings.values()
        ]
        fig = go.Figure(go.Bar(
            x=[stock_label(s) for s in symbols],
            y=vals,
            marker_color=[
                COLORS["primary"] if v >= 0 else COLORS["danger"]
                for v in vals
            ],
        ))
        fig.update_layout(**plotly_layout(xaxis_title="标的", yaxis_title="市值 ($)"))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📈 盈亏分布")
        pnls = [h.get("unrealized_pnl", 0) for h in holdings.values()]
        fig = go.Figure(go.Bar(
            x=[stock_label(s) for s in symbols],
            y=pnls,
            marker_color=[
                COLORS["secondary"] if p >= 0 else COLORS["danger"]
                for p in pnls
            ],
        ))
        fig.update_layout(**plotly_layout(xaxis_title="标的", yaxis_title="盈亏 ($)"))
        st.plotly_chart(fig, use_container_width=True)

    # ── 持仓明细 ──
    st.subheader("📋 持仓明细")
    rows = []
    for sym, h in holdings.items():
        rows.append({
            "标的":     stock_label(sym),
            "股数":     h.get("current_shares", 0),
            "调整成本": f"${h.get('adjusted_cost', 0):.2f}",
            "权利金":   f"${h.get('total_premiums', 0):,.2f}",
            "期权盈亏": f"${h.get('option_pnl', 0):,.2f}",
            "浮动盈亏": f"${h.get('unrealized_pnl', 0):,.2f}",
            "总盈亏":   f"${h.get('total_pnl', 0):,.2f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
