"""页面：期权车轮 Options Wheel"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_transactions
from src import WheelCalculator

from .config import COLORS, ACTION_CN, ACTION_LABELS
from .helpers import (
    fetch_exchange_rates, dict_to_transaction,
    plotly_layout, metric_row, stock_label,
)


# ── 辅助 ──

OPTION_ACTIONS = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}
STOCK_ACTIONS  = {"BUY", "SELL", "ASSIGNMENT", "CALLED_AWAY"}


def _heading(title: str):
    st.markdown(
        "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px'>" + title + "</h3>",
        unsafe_allow_html=True,
    )


def _annualized_return(premium: float, cost_basis: float, days_held: int) -> float:
    """(权利金 / 成本) × (365 / 天数) × 100"""
    if cost_basis <= 0 or days_held <= 0:
        return 0.0
    return (premium / cost_basis) * (365 / days_held) * 100


# ── 页面 ──

def page_wheel():
    st.markdown(
        "<h1 style='margin-bottom:4px'>期权车轮</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>成本基准 · 年化收益 · 回本预测 · 热力图</p>",
        unsafe_allow_html=True,
    )

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]

    tx_raw = get_transactions(category="投资", limit=500)

    # 收集所有做过期权的标的
    option_symbols = sorted(set(
        t["symbol"] for t in tx_raw
        if t.get("action") in OPTION_ACTIONS and t.get("symbol")
    ))

    if not option_symbols:
        st.info("暂无期权交易记录，去 📝 交易日志 添加吧！")
        return

    # 全量 Transaction (股票 + 期权)
    all_relevant = [
        t for t in tx_raw
        if t.get("symbol") in option_symbols
        and t.get("action") in (OPTION_ACTIONS | STOCK_ACTIONS)
    ]
    transactions = [dict_to_transaction(t) for t in all_relevant]
    wheel_calc = WheelCalculator(transactions)

    # ═══════════════════════════════════════════════════
    #  1️⃣  全标的概览卡片
    # ═══════════════════════════════════════════════════
    _heading("期权标的总览")

    overview_rows = []
    for sym in option_symbols:
        basis    = wheel_calc.calculate_adjusted_cost_basis(sym)
        premiums = wheel_calc.option_calc.get_premiums_summary(sym)
        shares   = basis.get("current_shares", 0)

        # 车轮周期状态
        cycle = wheel_calc.get_wheel_cycle_info(sym)
        _status_map = {
            "holding": "🔵 持股中 · 卖Call",
            "waiting": "🟡 等待接盘 · 卖Put",
            "empty":   "⚪ 无交易",
        }
        status_label = _status_map.get(cycle.get("status", ""), "—")

        sym_dates = [t["datetime"][:10] for t in all_relevant if t["symbol"] == sym]
        first_date = min(sym_dates) if sym_dates else ""
        days_held  = (datetime.now() - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date else 0

        net_prem   = premiums.get("net_premium", 0)
        cost_basis = basis.get("cost_basis", 0)
        adj_cost   = basis.get("adjusted_cost", 0)
        ann_ret    = _annualized_return(net_prem, cost_basis, days_held) if cost_basis > 0 else 0

        overview_rows.append({
            "标的": stock_label(sym),
            "滚动状态": status_label,
            "持仓(股)": int(shares),
            "原始成本/股": f"${cost_basis / shares:.2f}" if shares else "-",
            "调整后成本/股": f"${adj_cost:.2f}" if shares else "-",
            "净权利金": f"${net_prem:,.2f}",
            "累计年化%": f"{ann_ret:.1f}%",
            "持有天数": days_held,
        })

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════
    #  选择标的 → 详细分析
    # ═══════════════════════════════════════════════════
    selected = st.selectbox(
        "选择标的进行详细分析",
        option_symbols,
        format_func=stock_label,
    )

    basis    = wheel_calc.calculate_adjusted_cost_basis(selected)
    premiums = wheel_calc.option_calc.get_premiums_summary(selected)
    shares   = int(basis.get("current_shares", 0))

    _heading(f"{stock_label(selected)} 详细分析")

    # ── 核心指标 ──
    net_prem    = premiums.get("net_premium", 0)
    collected   = premiums.get("total_collected", 0)
    paid        = premiums.get("total_paid", 0)
    cost_basis  = basis.get("cost_basis", 0)
    adj_cost    = basis.get("adjusted_cost", 0)
    total_fees  = sum(t.fees for t in transactions if t.symbol == selected)

    metric_row([
        ("权利金收入",  f"${collected:,.2f}"),
        ("权利金支出",  f"${paid:,.2f}"),
        ("净权利金",    f"${net_prem:,.2f}"),
        ("调整后成本",  f"${adj_cost:.2f}/股" if shares else "-"),
        ("持仓",        f"{shares} 股"),
    ])

    # ═══════════════════════════════════════════════════
    #  2️⃣  成本基准下降折线图
    # ═══════════════════════════════════════════════════
    sym_txs = sorted(
        [t for t in all_relevant if t["symbol"] == selected],
        key=lambda t: t["datetime"],
    )

    running_stock_cost = 0.0
    running_premium    = 0.0
    running_fees       = 0.0
    running_shares     = 0
    cost_timeline      = []

    for t in sym_txs:
        action = t["action"]
        qty    = t.get("quantity", 0)
        price  = t.get("price", 0)
        fees   = t.get("fees", 0)
        dt     = t["datetime"][:10]

        if action in ("BUY", "ASSIGNMENT"):
            running_stock_cost += price * qty
            running_shares += qty
        elif action in ("SELL", "CALLED_AWAY"):
            running_stock_cost -= price * qty
            running_shares -= qty
        elif action in OPTION_ACTIONS:
            mult = 100
            if action in ("STO", "STO_CALL"):
                running_premium += price * qty * mult
            else:
                running_premium -= price * qty * mult

        running_fees += fees

        if running_shares > 0:
            adj = (running_stock_cost - running_premium + running_fees) / running_shares
            cost_timeline.append({
                "日期": dt,
                "调整后成本/股": round(adj, 2),
                "操作": ACTION_CN.get(action, action),
            })

    if cost_timeline:
        cdf = pd.DataFrame(cost_timeline)
        _heading("成本基准变化")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cdf["日期"], y=cdf["调整后成本/股"],
            mode="lines+markers+text",
            text=[f"${v:.2f}" for v in cdf["调整后成本/股"]],
            textposition="top center",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=10),
            hovertext=cdf["操作"],
        ))
        fig.update_layout(
            **plotly_layout(height=350),
            yaxis_title="成本/股 ($)",
            xaxis_title="日期",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  3️⃣  每笔期权交易年化收益 + 累计收益曲线
    # ═══════════════════════════════════════════════════
    option_txs = [t for t in sym_txs if t["action"] in OPTION_ACTIONS]

    if option_txs and shares > 0:
        stock_buy_dates = [
            t["datetime"][:10] for t in sym_txs
            if t["action"] in ("BUY", "ASSIGNMENT")
        ]
        base_date = (
            datetime.strptime(min(stock_buy_dates), "%Y-%m-%d")
            if stock_buy_dates else datetime.now()
        )
        raw_stock_cost = sum(
            t["price"] * t["quantity"]
            for t in sym_txs if t["action"] in ("BUY", "ASSIGNMENT")
        )

        trade_details = []
        cumulative_premium = 0.0

        for t in option_txs:
            act   = t["action"]
            qty   = t.get("quantity", 0)
            price = t.get("price", 0)
            fees  = t.get("fees", 0)
            dt    = t["datetime"][:10]

            premium_usd = price * qty * 100
            is_income = act in ("STO", "STO_CALL")
            net_income = premium_usd - fees if is_income else -(premium_usd + fees)
            cumulative_premium += net_income

            days = max((datetime.strptime(dt, "%Y-%m-%d") - base_date).days, 1)
            single_return_pct = (
                (abs(net_income) / raw_stock_cost) * 100 if raw_stock_cost > 0 else 0
            )
            ann_ret = (
                (abs(net_income) / raw_stock_cost) * (365 / days) * 100
                if raw_stock_cost > 0 else 0
            )

            trade_details.append({
                "日期": dt,
                "操作": ACTION_CN.get(act, act),
                "张数": qty,
                "权利金/张": f"${price:.2f}",
                "总额(含×100)": f"${premium_usd:,.0f}",
                "手续费": f"${fees:.2f}",
                "净收入": f"${net_income:,.2f}",
                "单笔收益%": f"{single_return_pct:.2f}%" if is_income else f"-{single_return_pct:.2f}%",
                "年化收益%": f"{ann_ret:.1f}%" if is_income else f"-{ann_ret:.1f}%",
                "_cum": cumulative_premium,
                "_date": dt,
            })

        left_col, right_col = st.columns(2)

        with left_col:
            _heading("逐笔交易年化收益")
            display_df = pd.DataFrame(trade_details)[
                ["日期", "操作", "张数", "权利金/张", "总额(含×100)",
                 "手续费", "净收入", "单笔收益%", "年化收益%"]
            ]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        with right_col:
            _heading("累计权利金收益曲线")
            cum_df = pd.DataFrame(trade_details)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cum_df["_date"], y=cum_df["_cum"],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color=COLORS["primary"], width=2),
                marker=dict(size=8),
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                **plotly_layout(height=350),
                yaxis_title="累计净权利金 ($)",
                xaxis_title="日期",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  4️⃣  盈亏分析 & 回本预测
    # ═══════════════════════════════════════════════════
    if shares > 0 and cost_basis > 0:
        _heading("盈亏分析 & 回本预测")

        # ── Net Basis = 持仓成本 − 已收权利金 ──
        stock_only_cost = sum(
            t["price"] * t["quantity"]
            for t in sym_txs if t["action"] in ("BUY", "ASSIGNMENT")
        )
        net_basis = stock_only_cost - net_prem  # 净成本基准
        net_basis_per_share = net_basis / shares if shares else 0

        # 获取当前股价
        try:
            from api.stock_data import get_current_price
            cur_info = get_current_price(selected)
            cur_price = cur_info.get("price", 0) if cur_info else 0
        except Exception:
            cur_price = 0

        # 对比当前股价与净成本
        net_pnl_vs_price = (cur_price - net_basis_per_share) * shares if cur_price and shares else 0

        if option_txs:
            first_opt_date = datetime.strptime(option_txs[0]["datetime"][:10], "%Y-%m-%d")
            last_opt_date  = datetime.strptime(option_txs[-1]["datetime"][:10], "%Y-%m-%d")
            weeks_active   = max((last_opt_date - first_opt_date).days / 7, 1)
            avg_weekly_prem = net_prem / weeks_active
        else:
            avg_weekly_prem = 0
            weeks_active = 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("原始股票成本", f"${stock_only_cost:,.0f}")
        c2.metric("净成本基准", f"${net_basis:,.0f}")
        c3.metric("净成本/股", f"${net_basis_per_share:.2f}")
        if cur_price:
            c4.metric("当前股价", f"${cur_price:.2f}",
                      delta=f"vs净成本 ${cur_price - net_basis_per_share:+.2f}")
        else:
            c4.metric("当前股价", "—")
        c5.metric("每周均权利金", f"${avg_weekly_prem:,.2f}")

        if avg_weekly_prem > 0 and net_basis > 0:
            weeks_to_zero = net_basis / avg_weekly_prem
            st.info(
                f"以每周 ${avg_weekly_prem:.2f} 权利金计算，预计 **{weeks_to_zero:.0f} 周"
                f"（{weeks_to_zero / 4.33:.0f} 月）** 完全回本"
            )

        progress = (
            min(net_prem / stock_only_cost, 1.0)
            if stock_only_cost > 0 else 0
        )
        st.progress(progress, text=f"回本进度 {progress * 100:.1f}%")

    # ═══════════════════════════════════════════════════
    #  5️⃣  收益率热力图（按月×操作类型）
    # ═══════════════════════════════════════════════════
    if option_txs:
        _heading("收益率热力图（月 × 操作类型）")
        heat_rows = []
        for t in option_txs:
            month = t["datetime"][:7]
            act   = ACTION_CN.get(t["action"], t["action"])
            prem  = t["price"] * t["quantity"] * 100
            is_income = t["action"] in ("STO", "STO_CALL")
            heat_rows.append({
                "月份": month,
                "操作": act,
                "金额": prem if is_income else -prem,
            })

        heat_df = pd.DataFrame(heat_rows)
        pivot = heat_df.pivot_table(
            index="操作", columns="月份", values="金额",
            aggfunc="sum", fill_value=0,
        )
        if not pivot.empty:
            fig = go.Figure(go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale=[
                    [0, "#C0392B"], [0.35, "#E8A0A0"],
                    [0.5, "#FAFAFA"],
                    [0.65, "#A0D8A0"], [1, "#2E8B57"],
                ],
                zmid=0,
                text=[[f"${v:,.0f}" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                textfont=dict(size=12, family="'Times New Roman', serif"),
                hovertemplate="月份: %{x}<br>操作: %{y}<br>金额: %{text}<extra></extra>",
            ))
            fig.update_layout(
                **plotly_layout(height=300),
                xaxis_title="月份",
                yaxis_title="操作类型",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  6️⃣  操作分布 + 权利金时间线
    # ═══════════════════════════════════════════════════
    df_opt = pd.DataFrame(
        [t for t in all_relevant
         if t["symbol"] == selected and t["action"] in OPTION_ACTIONS]
    )
    if not df_opt.empty:
        df_opt["date"] = pd.to_datetime(df_opt["datetime"])

        left, right = st.columns(2)

        with left:
            _heading("权利金时间线")
            df_opt["premium_real"] = df_opt.apply(
                lambda r: r["price"] * r["quantity"] * 100
                * (1 if r["action"] in ("STO", "STO_CALL") else -1),
                axis=1,
            )
            monthly = df_opt.groupby(
                df_opt["date"].dt.strftime("%Y-%m")
            )["premium_real"].sum()
            if not monthly.empty:
                fig = go.Figure(go.Bar(
                    x=monthly.index,
                    y=monthly.values,
                    marker_color=[
                        COLORS["primary"] if v > 0 else COLORS["danger"]
                        for v in monthly.values
                    ],
                    text=[f"${v:,.0f}" for v in monthly.values],
                    textposition="outside",
                ))
                fig.update_layout(**plotly_layout(height=300), yaxis_title="权利金 ($)")
                st.plotly_chart(fig, use_container_width=True)

        with right:
            _heading("操作分布")
            act_counts = df_opt["action"].value_counts()
            fig = go.Figure(go.Pie(
                labels=[ACTION_LABELS.get(a, a) for a in act_counts.index],
                values=act_counts.values,
                hole=0.4,
                marker=dict(colors=[
                    COLORS["primary"], COLORS["danger"], COLORS["warning"],
                    COLORS["secondary"], COLORS["purple"], COLORS["blue_light"],
                ]),
            ))
            fig.update_layout(**plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  7️⃣  期权交易明细
    # ═══════════════════════════════════════════════════
    _heading("期权交易明细")
    if not df_opt.empty:
        d = df_opt[["datetime", "action", "quantity", "price", "fees"]].copy()
        d["日期"]       = pd.to_datetime(d["datetime"]).dt.strftime("%Y-%m-%d")
        d["权利金(总)"] = d["quantity"] * d["price"] * 100
        d["权利金_RMB"] = d["权利金(总)"] * usd_rmb
        d["操作"]       = d["action"].map(ACTION_LABELS).fillna(d["action"])
        d = d[["日期", "操作", "quantity", "price", "权利金(总)", "fees", "权利金_RMB"]]
        d.columns = ["日期", "操作", "张数", "权利金/张(USD)", "权利金(USD)", "手续费", "权利金(RMB)"]
        st.dataframe(d, use_container_width=True, hide_index=True)

    with st.expander("💡 术语说明"):
        st.markdown("""
| 概念 | 说明 | 示例 |
|------|------|------|
| **1 张期权 = 100 股** | 权利金总额 = 单价 × 张数 × 100 | 卖 1 张 $2.60 → 收入 $260 |
| **权利金 (Premium)** | 买卖期权的价格 | STO AAPL 150P → 收 $3.50/股 |
| **行权价 (Strike)** | 到期时约定的买卖价 | Strike = $150 |
| **年化收益率** | (净收入/成本) × (365/天数) | 2天赚0.5% → 年化91.25% |
| **手续费** | 按张计，不乘100 | 1 张手续费 $0.65 |
        """)
