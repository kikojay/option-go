"""子页面 1 — 总览趋势 (Performance)"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from ui import UI, plotly_layout
from services import PortfolioService
import db


def render(data: dict) -> None:
    """渲染总览趋势 Tab"""
    metrics = PortfolioService.calc_overview_metrics(data)
    total_value = metrics["total_value"]
    total_cost = metrics["total_cost"]
    total_pnl = metrics["total_pnl"]
    usd_rmb = metrics["usd_rmb"]

    UI.metric_row([
        ("总市值 (USD)", f"${total_value:,.0f}"),
        ("折合人民币",   f"¥{total_value * usd_rmb:,.0f}"),
        ("持仓成本",     f"${total_cost:,.0f}"),
        ("浮动盈亏",     f"${total_pnl:,.0f}", f"${total_pnl:+,.0f}"),
    ])
    UI.divider()

    _render_capital_flow_section(data)
    _render_trend_charts(data)


def _render_capital_flow_section(data: dict) -> None:
    """入金/出金表单和历史记录"""
    with UI.expander("入金/出金记录（影响收益率计算）", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        dep_type = c1.selectbox(
            "类型", ["DEPOSIT", "WITHDRAW"],
            format_func=lambda x: "入金" if x == "DEPOSIT" else "出金",
            key="dep_type")
        dep_amount = c2.number_input("金额 (USD)", value=0.0, step=100.0,
                                     key="dep_amount")
        dep_date = c3.date_input("日期", value=datetime.now().date(),
                                 key="dep_date")
        dep_note = c4.text_input("备注", placeholder="例: 追加资金",
                                 key="dep_note")

        if st.button("保存", key="btn_save_deposit"):
            if dep_amount > 0:
                db.transactions.add(
                    dep_date.strftime("%Y-%m-%d"),
                    dep_type, quantity=1,
                    price=dep_amount, currency="USD",
                    note=dep_note or ("入金" if dep_type == "DEPOSIT" else "出金"))
                st.success("已保存！")
                st.rerun()
            else:
                st.error("金额必须大于 0")

        cf_table = PortfolioService.build_capital_flow_table(
            data.get("capital_flows", []))
        if cf_table is not None:
            display = cf_table.rename(columns={
                "date": "日期",
                "action_label": "类型",
                "amount_usd": "金额(USD)",
                "note": "备注",
            })
            UI.table(display, max_height=300)


def _render_trend_charts(data: dict) -> None:
    """总资产增长曲线 + TWR 收益率"""
    UI.sub_heading("总资产增长曲线")

    merged = PortfolioService.build_trend_data(data)
    if merged is None:
        st.caption("暂无快照数据，无法绘制走势图。请先到「月度快照」页面生成快照。")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="总市值", x=merged["date"], y=merged["total_usd"],
        mode="lines+markers",
        line=dict(color="#2B4C7E", width=3.5, shape="spline"),
        marker=dict(size=12, color="#2B4C7E",
                    line=dict(color="#F9F7F0", width=2)),
        hovertemplate="%{x}<br>市值: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        name="本金投入", x=merged["date"], y=merged["deposit"],
        mode="lines",
        line=dict(color="#D4A017", width=2, dash="dot"),
        hovertemplate="%{x}<br>本金: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        name="真实收益", x=merged["date"], y=merged["gain"],
        mode="lines",
        line=dict(color="#5B8C5A", width=2, dash="dash"),
        hovertemplate="%{x}<br>收益: $%{y:,.0f}<extra></extra>"))
    fig.update_layout(**plotly_layout(
        height=360, margin=dict(l=55, r=15, t=10, b=40),
        hovermode="x unified", yaxis_title="金额 ($)"))
    st.plotly_chart(fig, use_container_width=True, key="port_trend")

    # TWR 收益率
    UI.sub_heading("累计收益率 (Time-Weighted)")
    fig2 = go.Figure(go.Scatter(
        x=merged["date"], y=merged["twr_pct"],
        mode="lines+markers",
        line=dict(color="#5B8C5A", width=3.5, shape="spline"),
        marker=dict(size=12, color="#5B8C5A",
                    line=dict(color="#F9F7F0", width=2)),
        fill="tozeroy", fillcolor="rgba(91,140,90,0.08)",
        hovertemplate="%{x}<br>收益率: %{y:.1f}%<extra></extra>"))
    fig2.add_hline(y=0, line_dash="dash", line_color="#C8C3B5")
    fig2.update_layout(**plotly_layout(
        height=280, margin=dict(l=55, r=15, t=10, b=40),
        yaxis_title="收益率 (%)"))
    fig2.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig2, use_container_width=True, key="port_twr")
