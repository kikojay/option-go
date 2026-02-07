"""页面：总览 Overview"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict

from src.database_v2 import get_all_accounts, get_transactions, get_all_snapshots
from src import PortfolioCalculator

from .config import COLORS, CATEGORY_CN
from .helpers import (
    fetch_exchange_rates, to_rmb, dict_to_transaction,
    plotly_layout, metric_row, stock_label,
)


def page_overview():
    st.title("📊 总览 Overview")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ── 汇率信息 + 折线图 ──
    st.subheader("💱 实时汇率")
    st.info(f"1 USD = ¥{usd_rmb:.4f} CNY · 1 HKD = ¥{hkd_rmb:.4f} CNY")

    # 汇率走势（用最近一段的模拟趋势线，因为只有实时数据点）
    # 展示一个简洁的汇率仪表盘
    c1, c2, c3 = st.columns(3)
    c1.metric("🇺🇸 美元/人民币", f"¥{usd_rmb:.4f}")
    c2.metric("🇭🇰 港币/人民币", f"¥{hkd_rmb:.4f}")
    c3.metric("🇺🇸 美元/港币", f"HK${usd_rmb / hkd_rmb:.4f}" if hkd_rmb > 0 else "-")

    accounts = get_all_accounts()

    # ── 总资产计算 ──
    total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
    total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
    total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
    total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

    # ── 投资组合 ──
    tx_raw = get_transactions(category="投资", limit=500)
    transactions = [dict_to_transaction(t) for t in tx_raw]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💰 总资产")
        metric_row([
            ("美元 (USD)", f"${total_usd:,.0f}"),
            ("人民币 (CNY)", f"¥{total_cny:,.0f}"),
            ("折合人民币总计", f"¥{total_rmb:,.0f}"),
        ])

    with col_right:
        st.subheader("📈 投资组合")
        if transactions:
            calc = PortfolioCalculator(transactions)
            summary = calc.get_portfolio_summary()
            holdings = summary.get("holdings", {})
            market_val = sum(
                h.get("cost_basis", 0) for h in holdings.values()
            )
            metric_row([
                ("市值 (USD)", f"${market_val:,.0f}"),
                ("浮动盈亏", f"${summary['total_unrealized_pnl']:,.0f}"),
            ])
        else:
            st.caption("暂无投资数据")

    # ── 图表行 ──
    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.subheader("🏦 资产配置")
        if accounts:
            # 按 category 聚合，翻译为中文标签
            cat_assets: Dict[str, float] = {}
            for a in accounts:
                cn_cat = CATEGORY_CN.get(a["category"], a["category"])
                cat_assets[cn_cat] = cat_assets.get(cn_cat, 0) + to_rmb(
                    a["balance"], a["currency"], rates
                )
            # 去掉零值
            cat_assets = {k: v for k, v in cat_assets.items() if v > 0}
            if cat_assets:
                fig = go.Figure(go.Pie(
                    labels=list(cat_assets.keys()),
                    values=list(cat_assets.values()),
                    hole=0.5,
                    marker=dict(colors=px.colors.qualitative.Set3),
                    textinfo="label+percent",
                ))
                fig.update_layout(**plotly_layout(height=340))
                st.plotly_chart(fig, use_container_width=True)

    with chart_right:
        st.subheader("📈 总资产走势")
        snapshots = get_all_snapshots()
        if snapshots:
            sdf = pd.DataFrame(snapshots)
            fig = go.Figure(go.Scatter(
                x=sdf["date"],
                y=sdf["total_assets_rmb"],
                mode="lines+markers",
                name="总资产 (RMB)",
                line=dict(color=COLORS["primary"], width=3),
                fill="tozeroy",
                fillcolor="rgba(26,115,232,0.08)",
            ))
            fig.update_layout(**plotly_layout(
                height=340,
                xaxis_title="日期",
                yaxis_title="总资产 (¥)",
                hovermode="x unified",
            ))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("暂无快照数据，去「月度快照」页面创建")

    # ── 账户明细 ──
    st.subheader("🏦 账户明细")
    if accounts:
        rows = []
        for a in accounts:
            rows.append({
                "账户": a["name"],
                "类别": CATEGORY_CN.get(a["category"], a["category"]),
                "币种": a["currency"],
                "原币余额": a["balance"],
                "折合(RMB)": round(to_rmb(a["balance"], a["currency"], rates), 2),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
