"""子页面 3 — 期权策略 (Options Wheel)"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui import UI, plotly_layout
from services import PortfolioService
from config import ACTION_CN
from api.stock_names import get_stock_label as stock_label
from services._legacy import dict_to_transaction, WheelStrategyCalculator as WheelCalculator


def render(data: dict) -> None:
    """渲染期权策略 Tab"""
    tx_raw = data["tx_raw"]

    option_symbols = PortfolioService.get_option_symbols(tx_raw)
    if not option_symbols:
        st.info("暂无期权交易记录")
        return

    all_relevant = PortfolioService.get_all_relevant_tx(tx_raw, option_symbols)

    # 构建 WheelCalculator
    transactions = [dict_to_transaction(t) for t in all_relevant]
    wheel_calc = WheelCalculator(transactions)

    _render_overview_table(option_symbols, all_relevant, wheel_calc)
    _render_detail(option_symbols, all_relevant, wheel_calc, data["usd_rmb"])


def _render_overview_table(option_symbols, all_relevant, wheel_calc):
    """标的总览表"""
    UI.sub_heading("期权标的总览")
    overview_rows = PortfolioService.build_options_overview(
        option_symbols, all_relevant, wheel_calc, stock_label)

    odf = pd.DataFrame(overview_rows)
    st.dataframe(
        odf, use_container_width=True, hide_index=True,
        column_config={
            "symbol_label": st.column_config.TextColumn("标的"),
            "status_label": st.column_config.TextColumn("状态"),
            "shares": st.column_config.NumberColumn("持仓(股)", format="%d"),
            "net_premium": st.column_config.NumberColumn("净权利金", format="$%,.2f"),
            "dividends": st.column_config.NumberColumn("累计分红", format="$%,.2f"),
            "adjusted_cost_per_share": st.column_config.NumberColumn(
                "调整成本/股", format="$%.2f"
            ),
            "annualized_pct": st.column_config.NumberColumn("年化%", format="%.1f%%"),
            "weeks_to_zero": st.column_config.NumberColumn("预计回本(周)", format="%.1f"),
            "days_held": st.column_config.NumberColumn("天数", format="%d"),
        })


def _render_detail(option_symbols, all_relevant, wheel_calc, usd_rmb):
    """选定标的的详情面板"""
    selected = st.selectbox(
        "选择标的查看详情", option_symbols,
        format_func=stock_label, key="port_opt_sel")

    detail = PortfolioService.build_option_detail(
        selected, all_relevant, wheel_calc)

    shares = detail["shares"]
    UI.metric_row([
        ("权利金收入", f"${detail['collected']:,.2f}"),
        ("权利金支出", f"${detail['paid']:,.2f}"),
        ("净权利金",   f"${detail['net_prem']:,.2f}"),
        ("累计分红",   f"${detail['dividends']:,.2f}"),
        ("调整成本",   f"${detail['adj_cost']:.2f}/股" if shares else "—"),
        ("持仓",       f"{shares} 股"),
    ])

    # 回本预测
    recovery = detail["recovery"]
    if recovery:
        UI.divider()
        UI.metric_row([
            ("每周均权利金", f"${recovery['avg_weekly']:,.2f}"),
            ("剩余成本",     f"${recovery['remaining']:,.0f}"),
            ("预计回本",     f"{recovery['weeks_to_zero']:.0f} 周 "
                           f"({recovery['months_to_zero']:.0f} 月)"),
        ])
        st.progress(
            recovery["progress"],
            text=(f"回本进度 {recovery['progress'] * 100:.1f}%  "
                  f"(权利金 ${recovery['net_prem']:,.0f} "
                  f"+ 分红 ${recovery['dividends']:,.0f})"
                  f" / 成本 ${recovery['cost_basis']:,.0f}"))

    # 成本基准变化图
    cost_timeline = detail["cost_timeline"]
    if cost_timeline:
        UI.sub_heading(f"{stock_label(selected)} 成本基准变化")
        cdf = pd.DataFrame(cost_timeline)
        if "date" not in cdf.columns:
            cdf = cdf.rename(columns={
                "日期": "date",
                "成本/股": "cost_per_share",
                "操作": "action",
            })
        cdf["action_cn"] = cdf["action"].map(ACTION_CN).fillna(cdf["action"])

        fig = go.Figure(go.Scatter(
            x=cdf["date"], y=cdf["cost_per_share"],
            mode="lines+markers+text",
            text=[f"${v:.2f}" for v in cdf["cost_per_share"]],
            textposition="top center",
            textfont=dict(size=11, family="'Times New Roman', serif"),
            line=dict(color="#2B4C7E", width=3.5),
            marker=dict(size=12, color="#2B4C7E",
                        line=dict(color="#F9F7F0", width=2)),
            hovertext=cdf["action_cn"]))
        fig.update_layout(**plotly_layout(
            height=320, margin=dict(l=55, r=15, t=10, b=40),
            yaxis_title="成本/股 ($)"))
        st.plotly_chart(fig, use_container_width=True, key="port_opt_cost")
