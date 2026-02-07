"""总览页面 — 资产概览与趋势"""
import streamlit as st
import plotly.graph_objects as go

from ui import UI, plotly_layout
from services import OverviewService


def render():
    UI.inject_css()
    UI.header("总资产概览", "Net Worth Overview")

    usd_rmb = st.session_state.usd_rmb
    hkd_rmb = st.session_state.hkd_rmb

    # 1. 指标卡片
    m = OverviewService.get_metrics(usd_rmb, hkd_rmb)

    c1, c2, c3 = st.columns(3)
    with c1:
        UI.card("总资产", m["total_rmb"], delta=m["delta_percent"],
                subtext=f"折合 ${m['total_rmb'] / usd_rmb:,.0f} USD")
    with c2:
        UI.card("美元资产", m["total_usd"] * usd_rmb,
                subtext=f"${m['total_usd']:,.0f} x {usd_rmb:.2f}")
    with c3:
        UI.card("人民币资产", m["total_cny"], subtext="CNY 账户余额")

    # 2. 饼图 + 趋势
    col_pie, col_trend = st.columns([1, 1.3])

    with col_pie:
        UI.sub_heading("资产配置")
        bd = m["cat_breakdown"]
        pos = [b for b in bd if b["value"] > 0]
        if pos:
            fig = go.Figure(go.Pie(
                labels=[b["cat"] for b in pos],
                values=[b["value"] for b in pos],
                hole=0,
                marker=dict(
                    colors=[b["color"] for b in pos],
                    line=dict(color="#F9F7F0", width=2)),
                textinfo="label+percent",
                textfont=dict(size=14,
                              family="'Times New Roman', Georgia, serif",
                              color="#FFFFFF"),
                insidetextorientation="radial",
                hovertemplate="%{label}<br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
                sort=False,
            ))
            fig.update_layout(**plotly_layout(
                height=420, margin=dict(l=5, r=5, t=10, b=10),
                showlegend=False))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False},
                            key="overview_pie")

    with col_trend:
        UI.sub_heading("总资产增长曲线")
        trend = OverviewService.get_trend()
        if trend is not None:
            fig = go.Figure(go.Scatter(
                x=trend["date"], y=trend["asset_wan"],
                mode="lines+markers",
                line=dict(color="#2B4C7E", width=3.5, shape="spline"),
                marker=dict(size=12, color="#2B4C7E", symbol="circle",
                            line=dict(color="#F9F7F0", width=2)),
                hovertemplate="%{x}<br><b>¥%{y:.2f} 万</b><extra></extra>",
            ))
            fig.update_layout(**plotly_layout(
                height=420, margin=dict(l=55, r=15, t=10, b=40),
                hovermode="x unified", showlegend=False))
            fig.update_yaxes(title="万元", ticksuffix=" 万")
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False},
                            key="overview_trend")
        else:
            st.caption("暂无快照数据，去「月度快照」页面创建")

    # 3. 明细折叠
    with UI.expander("查看资产明细", expanded=False):
        bd = m["cat_breakdown"]
        if bd and m["total_rmb"] > 0:
            import pandas as pd
            rows = [{"资产类别": b["cat"],
                     "价值 (¥)": b["value"],
                     "占比": f"{b['value'] / m['total_rmb'] * 100:.1f}%"}
                    for b in bd]
            UI.table(pd.DataFrame(rows))
        else:
            st.info("暂无账户数据")
