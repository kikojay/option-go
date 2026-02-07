"""期权车轮页面 — 成本基准 · 年化收益 · 回本预测 · 热力图"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui import UI, plotly_layout
from services import WheelService
from config import COLORS, OPTION_ACTION_LABELS
from api.stock_names import get_stock_label as stock_label


def render():
    UI.inject_css()
    UI.header("期权车轮", "成本基准 · 年化收益 · 回本预测 · 热力图")

    data = WheelService.load()
    if data is None:
        UI.empty("暂无期权交易记录，去交易日志添加吧！")
        return

    syms = data["option_symbols"]
    all_rel = data["all_relevant"]
    wc = data["wheel_calc"]

    # 1. 概览表
    UI.sub_heading("期权标的总览")
    rows = WheelService.overview_rows(syms, all_rel, wc, stock_label)
    UI.table(pd.DataFrame(rows))

    # 2. 选择标的
    selected = st.selectbox("选择标的进行详细分析", syms,
                            format_func=stock_label)

    UI.sub_heading(f"{stock_label(selected)} 详细分析")
    dm = WheelService.detail_metrics(selected, all_rel, wc)
    UI.metric_row([
        ("权利金收入", f"${dm['collected']:,.2f}"),
        ("权利金支出", f"${dm['paid']:,.2f}"),
        ("净权利金",   f"${dm['net_prem']:,.2f}"),
        ("调整后成本", f"${dm['adj_cost']:.2f}/股" if dm["shares"] else "-"),
        ("持仓",       f"{dm['shares']} 股"),
    ])

    # 3. 成本基准折线
    tl = WheelService.cost_timeline(selected, all_rel)
    if tl:
        _cost_chart(tl)

    # 4. 逐笔年化 + 累计曲线
    trades, _cum = WheelService.trade_details(selected, all_rel)
    if trades:
        _trade_section(trades)

    # 5. 盈亏分析 & 回本预测
    rec = WheelService.recovery(selected, all_rel, wc)
    if rec:
        _recovery_section(rec)

    # 6. 热力图
    pivot = WheelService.heatmap(all_rel, selected)
    if pivot is not None:
        _heatmap(pivot)

    # 7. 权利金时间线 + 操作分布
    bars = WheelService.premium_bars(all_rel, selected)
    dist = WheelService.action_dist(all_rel, selected)
    if bars is not None or dist is not None:
        _bottom_charts(bars, dist)

    # 8. 期权明细表
    usd_rmb = st.session_state.usd_rmb
    detail = WheelService.option_detail_table(all_rel, selected, usd_rmb)
    if detail is not None:
        UI.sub_heading("期权交易明细")
        display = detail.rename(columns={
            "date": "日期",
            "action_label": "操作",
            "quantity": "张数",
            "price": "权利金/张(USD)",
            "premium_total": "权利金(USD)",
            "fees": "手续费",
            "premium_rmb": "权利金(RMB)",
        })
        UI.table(display, max_height=500)

    # 术语说明
    with UI.expander("术语说明"):
        st.markdown(
            "| 概念 | 说明 |\n|------|------|\n"
            "| **1张=100股** | 权利金总额 = 单价 x 张数 x 100 |\n"
            "| **年化收益率** | (净收入/成本) x (365/天数) |\n"
            "| **手续费** | 按张计，不乘100 |")


# ── 渲染子函数 ─────────────────────────────────────────

def _cost_chart(tl):
    UI.sub_heading("成本基准变化")
    cdf = pd.DataFrame(tl)
    if "date" not in cdf.columns:
        cdf = cdf.rename(columns={
            "日期": "date",
            "成本/股": "cost_per_share",
            "操作": "action",
        })
    fig = go.Figure(go.Scatter(
        x=cdf["date"], y=cdf["cost_per_share"],
        mode="lines+markers+text",
        text=[f"${v:.2f}" for v in cdf["cost_per_share"]],
        textposition="top center",
        line=dict(color=COLORS["primary"], width=3.5),
        marker=dict(size=12, line=dict(color="#F9F7F0", width=2)),
        hovertext=cdf["action"].map(OPTION_ACTION_LABELS).fillna(cdf["action"])))
    fig.update_layout(**plotly_layout(height=350),
                      yaxis_title="成本/股 ($)", xaxis_title="日期")
    st.plotly_chart(fig, use_container_width=True)


def _trade_section(trades):
    left, right = st.columns(2)
    with left:
        UI.sub_heading("逐笔交易年化收益")
        tdf = pd.DataFrame(trades)
        if "date" not in tdf.columns:
            tdf = tdf.rename(columns={
                "日期": "date",
                "操作": "action",
                "张数": "quantity",
                "权利金/张": "price_per_contract",
                "总额(含x100)": "total_premium",
                "手续费": "fees",
                "净收入": "net_income",
                "单笔收益%": "single_return_pct",
                "年化收益%": "annualized_pct",
                "累计净权利金": "cumulative",
            })
        tdf["action_label"] = tdf["action"].map(OPTION_ACTION_LABELS).fillna(tdf["action"])
        display = tdf.rename(columns={
            "date": "日期",
            "action_label": "操作",
            "quantity": "张数",
            "price_per_contract": "权利金/张",
            "total_premium": "总额(含x100)",
            "fees": "手续费",
            "net_income": "净收入",
            "single_return_pct": "单笔收益%",
            "annualized_pct": "年化收益%",
        })
        cols = ["日期", "操作", "张数", "权利金/张", "总额(含x100)",
                "手续费", "净收入", "单笔收益%", "年化收益%"]
        UI.table(display[cols], max_height=400)
    with right:
        UI.sub_heading("累计权利金收益曲线")
        cum_df = pd.DataFrame(trades)
        if "date" not in cum_df.columns:
            cum_df = cum_df.rename(columns={
                "日期": "date",
                "累计净权利金": "cumulative",
            })
        fig = go.Figure(go.Scatter(
            x=cum_df["date"], y=cum_df["cumulative"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color=COLORS["primary"], width=3.5),
            marker=dict(size=12, line=dict(color="#F9F7F0", width=2))))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(**plotly_layout(height=350),
                          yaxis_title="累计净权利金 ($)", xaxis_title="日期")
        st.plotly_chart(fig, use_container_width=True)


def _recovery_section(rec):
    UI.sub_heading("盈亏分析 & 回本预测")
    UI.metric_row([
        ("原始股票成本", f"${rec['stock_cost']:,.0f}"),
        ("净成本基准", f"${rec['net_basis']:,.0f}"),
        ("净成本/股", f"${rec['nb_per_share']:.2f}"),
        ("当前股价", f"${rec['cur_price']:.2f}" if rec["cur_price"] else "—"),
        ("累计分红", f"${rec['dividends']:,.2f}"),
    ])
    if rec["avg_weekly"] > 0 and rec["net_basis"] > 0:
        w = rec["weeks_to_zero"]
        st.info(
            f"公式: (原始成本 ${rec['stock_cost']:,.0f}"
            f" - 权利金 ${rec['net_prem']:,.0f}"
            f" - 分红 ${rec['dividends']:,.0f})"
            f" / 每周 ${rec['avg_weekly']:.2f}"
            f" = **{w:.0f} 周（{w / 4.33:.0f} 月）** 完全回本")
    UI.progress_bar(rec["progress"], label="回本进度")


def _heatmap(pivot):
    UI.sub_heading("收益率热力图（月 x 操作类型）")
    y_labels = [OPTION_ACTION_LABELS.get(a, a) for a in pivot.index.tolist()]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=y_labels,
        colorscale=[[0, "#C0392B"], [0.35, "#E8A0A0"],
                    [0.5, "#FAFAFA"], [0.65, "#A0D8A0"], [1, "#2E8B57"]],
        zmid=0,
        text=[[f"${v:,.0f}" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=12, family="'Times New Roman', serif"),
        hovertemplate="月份: %{x}<br>操作: %{y}<br>金额: %{text}<extra></extra>"))
    fig.update_layout(**plotly_layout(height=300),
                      xaxis_title="月份", yaxis_title="操作类型")
    st.plotly_chart(fig, use_container_width=True)


def _bottom_charts(bars, dist):
    left, right = st.columns(2)
    with left:
        if bars is not None:
            UI.sub_heading("权利金时间线")
            fig = go.Figure(go.Bar(
                x=bars.index, y=bars.values,
                marker_color=[COLORS["primary"] if v > 0 else COLORS["danger"]
                              for v in bars.values],
                width=0.2,
                text=[f"${v:,.0f}" for v in bars.values],
                textposition="outside"))
            fig.update_layout(**plotly_layout(height=300),
                              yaxis_title="权利金 ($)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
    with right:
        if dist is not None:
            UI.sub_heading("操作分布")
            fig = go.Figure(go.Pie(
                labels=[OPTION_ACTION_LABELS.get(a, a) for a in dist.index],
                values=dist.values, hole=0.4,
                marker=dict(colors=[
                    COLORS["primary"], COLORS["danger"], COLORS["warning"],
                    COLORS["secondary"], COLORS["purple"],
                    COLORS.get("blue_light", "#3B7DD8")])))
            fig.update_layout(**plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)
