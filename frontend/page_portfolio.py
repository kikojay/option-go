"""页面：投资组合 Portfolio — 三子页面（总览趋势 / 持仓明细 / 期权策略）"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_transactions, get_all_snapshots
from src import PortfolioCalculator, WheelCalculator

from api.stock_data import get_batch_prices
from api.stock_names import get_stock_name
from .config import COLORS, ACTION_CN, ACTION_LABELS
from .helpers import (
    fetch_exchange_rates, dict_to_transaction,
    plotly_layout, metric_row, stock_label,
)


# ── helpers ──

OPTION_ACTIONS = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}
STOCK_ACTIONS  = {"BUY", "SELL", "ASSIGNMENT", "CALLED_AWAY"}


def _heading(title: str):
    st.markdown(
        "<h3 style='color:#1e293b;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px'>" + title + "</h3>",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════
#  公共数据加载（缓存在 session_state 避免重复查询）
# ════════════════════════════════════════════════════════

def _load_data():
    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]

    tx_raw = get_transactions(category="投资", limit=2000)
    if not tx_raw:
        return None

    transactions = [dict_to_transaction(t) for t in tx_raw]
    calc = PortfolioCalculator(transactions)
    summary = calc.get_portfolio_summary()
    holdings = summary.get("holdings", {})

    symbols_with_shares = [
        sym for sym, h in holdings.items()
        if int(h.get("current_shares", 0)) > 0
    ]
    live_prices = {}
    if symbols_with_shares:
        try:
            live_prices = get_batch_prices(symbols_with_shares)
        except Exception:
            pass

    return {
        "rates": rates,
        "usd_rmb": usd_rmb,
        "tx_raw": tx_raw,
        "transactions": transactions,
        "calc": calc,
        "summary": summary,
        "holdings": holdings,
        "live_prices": live_prices,
    }


# ════════════════════════════════════════════════════════
#  子页面 1 ── 总览趋势 (Overview)
# ════════════════════════════════════════════════════════

def _sub_overview(data):
    holdings = data["holdings"]
    usd_rmb = data["usd_rmb"]
    summary = data["summary"]
    live_prices = data["live_prices"]

    total_value = 0.0
    for sym, h in holdings.items():
        shares = int(h.get("current_shares", 0))
        if shares > 0:
            lp = live_prices.get(sym, {}).get("price", 0)
            total_value += lp * shares if lp else h.get("market_value", 0) or h.get("cost_basis", 0)
        else:
            total_value += h.get("market_value", 0) or 0

    total_cost = sum(h.get("cost_basis", 0) for h in holdings.values())
    total_pnl = summary["total_unrealized_pnl"]
    total_premiums = sum(h.get("total_premiums", 0) for h in holdings.values())

    metric_row([
        ("总市值 (USD)", f"${total_value:,.0f}"),
        ("折合人民币",   f"¥{total_value * usd_rmb:,.0f}"),
        ("持仓成本",     f"${total_cost:,.0f}"),
        ("浮动盈亏",     f"${total_pnl:,.0f}", f"${total_pnl:+,.0f}"),
    ])

    st.markdown('<hr style="border:none;border-top:1px solid #2D2D2D;margin:0.8rem 0">',
                unsafe_allow_html=True)

    # ── 总资产走势（从快照数据） ──
    _heading("总资产走势")

    snapshots = get_all_snapshots()
    if snapshots:
        sdf = pd.DataFrame(snapshots)
        sdf["date_parsed"] = pd.to_datetime(sdf["date"])
        sdf = sdf.sort_values("date_parsed")

        # 用快照的总资产 USD
        sdf["total_usd"] = sdf["total_assets_usd"]
        sdf["日期"] = sdf["date_parsed"].dt.strftime("%Y-%m-%d")

        # ── 手动入金估算：累计 BUY + ASSIGNMENT 的支出作为"本金投入" ──
        tx_raw = data["tx_raw"]
        deposit_records = []
        running_deposit = 0.0
        for t in sorted(tx_raw, key=lambda x: x["datetime"]):
            if t.get("action") in ("BUY", "ASSIGNMENT"):
                running_deposit += t.get("price", 0) * t.get("quantity", 0)
            dt = t["datetime"][:10]
            deposit_records.append({"date": dt, "deposit": running_deposit})

        if deposit_records:
            dep_df = pd.DataFrame(deposit_records).drop_duplicates(subset="date", keep="last")
            dep_df["date_parsed"] = pd.to_datetime(dep_df["date"])

            # 将 deposit 映射到快照日期（向后填充）
            merged = pd.merge_asof(
                sdf.sort_values("date_parsed"),
                dep_df[["date_parsed", "deposit"]].sort_values("date_parsed"),
                on="date_parsed",
                direction="backward",
            )
            merged["deposit"] = merged["deposit"].fillna(0)
            merged["gain"] = merged["total_usd"] - merged["deposit"]
        else:
            merged = sdf.copy()
            merged["deposit"] = 0
            merged["gain"] = merged["total_usd"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            name="总市值", x=merged["日期"], y=merged["total_usd"],
            mode="lines+markers",
            line=dict(color="#2B4C7E", width=3, shape="spline"),
            marker=dict(size=7, color="#2B4C7E",
                        line=dict(color="#F9F7F0", width=1.5)),
            hovertemplate="%{x}<br>市值: $%{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            name="本金投入", x=merged["日期"], y=merged["deposit"],
            mode="lines",
            line=dict(color="#D4A017", width=2, dash="dot"),
            hovertemplate="%{x}<br>本金: $%{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            name="累计收益", x=merged["日期"], y=merged["gain"],
            mode="lines",
            line=dict(color="#5B8C5A", width=2, dash="dash"),
            hovertemplate="%{x}<br>收益: $%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(**plotly_layout(
            height=360,
            margin=dict(l=55, r=15, t=10, b=40),
            hovermode="x unified",
            yaxis_title="金额 ($)",
        ))
        st.plotly_chart(fig, use_container_width=True, key="port_trend")

        # ── 累计收益率（时间加权: TWR 近似） ──
        _heading("累计收益率 (Time-Weighted)")

        merged["twr_pct"] = merged.apply(
            lambda r: ((r["total_usd"] - r["deposit"]) / r["deposit"] * 100)
            if r["deposit"] > 0 else 0,
            axis=1,
        )

        fig2 = go.Figure(go.Scatter(
            x=merged["日期"], y=merged["twr_pct"],
            mode="lines+markers",
            line=dict(color="#5B8C5A", width=3, shape="spline"),
            marker=dict(size=7, color="#5B8C5A",
                        line=dict(color="#F9F7F0", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(91,140,90,0.08)",
            hovertemplate="%{x}<br>收益率: %{y:.1f}%<extra></extra>",
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="#C8C3B5")
        fig2.update_layout(**plotly_layout(
            height=280,
            margin=dict(l=55, r=15, t=10, b=40),
            yaxis_title="收益率 (%)",
        ))
        fig2.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True, key="port_twr")

    else:
        st.caption("暂无快照数据，无法绘制走势图。请先到「月度快照」页面生成快照。")

    # ── 盈亏分布 ──
    _heading("标的盈亏分布")
    symbols = list(holdings.keys())
    pnls = [h.get("unrealized_pnl", 0) for h in holdings.values()]
    fig = go.Figure(go.Bar(
        x=[stock_label(s) for s in symbols],
        y=pnls,
        marker_color=[
            COLORS["secondary"] if p >= 0 else COLORS["danger"] for p in pnls
        ],
        text=[f"${p:+,.0f}" for p in pnls],
        textposition="outside",
        textfont=dict(size=12, family="'Times New Roman', serif"),
    ))
    fig.update_layout(**plotly_layout(
        height=300,
        margin=dict(l=55, r=15, t=15, b=50),
        xaxis_title="标的",
        yaxis_title="盈亏 ($)",
    ))
    st.plotly_chart(fig, use_container_width=True, key="port_pnl_bar")


# ════════════════════════════════════════════════════════
#  子页面 2 ── 持仓明细 (Holdings)
# ════════════════════════════════════════════════════════

def _sub_holdings(data):
    holdings = data["holdings"]
    live_prices = data["live_prices"]
    usd_rmb = data["usd_rmb"]

    _heading("持仓明细 · USD / RMB 双币对照")

    rows = []
    total_holding_cost = sum(
        h.get("cost_basis", 0) for h in holdings.values()
        if int(h.get("current_shares", 0)) > 0
    )
    for sym, h in holdings.items():
        shares = int(h.get("current_shares", 0))
        if shares <= 0:
            continue

        cost_basis = h.get("cost_basis", 0)
        adjusted_cost = h.get("adjusted_cost", 0)
        premiums = h.get("total_premiums", 0)
        pnl = h.get("unrealized_pnl", 0)
        pct = (cost_basis / total_holding_cost * 100) if total_holding_cost > 0 else 0

        price_info = live_prices.get(sym, {})
        current_price = price_info.get("price", 0)
        price_change = price_info.get("change_pct", 0)

        market_val_usd = current_price * shares if current_price else cost_basis
        market_val_rmb = market_val_usd * usd_rmb

        # ── 分红估算 (yfinance) ──
        est_annual_div = 0.0
        try:
            import yfinance as yf
            info = yf.Ticker(sym).info
            div_rate = info.get("dividendRate", 0) or 0
            est_annual_div = div_rate * shares
        except Exception:
            pass
        est_monthly_div = est_annual_div / 12

        rows.append({
            "代号": sym,
            "公司": get_stock_name(sym),
            "股数": shares,
            "现价($)": current_price,
            "涨跌%": price_change,
            "成本($)": cost_basis,
            "成本(¥)": round(cost_basis * usd_rmb),
            "市值($)": round(market_val_usd),
            "市值(¥)": round(market_val_rmb),
            "调整成本/股": adjusted_cost,
            "权利金": -premiums,
            "盈亏($)": pnl,
            "盈亏(¥)": round(pnl * usd_rmb),
            "月分红($)": round(est_monthly_div, 2),
            "年收息($)": round(est_annual_div, 2),
            "占比": pct / 100,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(450, 38 * (len(rows) + 1)),
            column_config={
                "代号": st.column_config.TextColumn("代号", width="small"),
                "公司": st.column_config.TextColumn("公司", width="small"),
                "股数": st.column_config.NumberColumn("股数", format="%d"),
                "现价($)": st.column_config.NumberColumn("现价($)", format="$%.2f"),
                "涨跌%": st.column_config.NumberColumn("涨跌%", format="%.2f%%"),
                "成本($)": st.column_config.NumberColumn("成本($)", format="$%,.0f"),
                "成本(¥)": st.column_config.NumberColumn("成本(¥)", format="¥%,.0f"),
                "市值($)": st.column_config.NumberColumn("市值($)", format="$%,.0f"),
                "市值(¥)": st.column_config.NumberColumn("市值(¥)", format="¥%,.0f"),
                "调整成本/股": st.column_config.NumberColumn("调整成本/股", format="$%.2f"),
                "权利金": st.column_config.NumberColumn("权利金", format="$%,.0f"),
                "盈亏($)": st.column_config.NumberColumn("盈亏($)", format="$%,.0f"),
                "盈亏(¥)": st.column_config.NumberColumn("盈亏(¥)", format="¥%,.0f"),
                "月分红($)": st.column_config.NumberColumn("预估月分红", format="$%.2f"),
                "年收息($)": st.column_config.NumberColumn("预估年收息", format="$%.2f"),
                "占比": st.column_config.ProgressColumn(
                    "占比", format="%.0f%%", min_value=0, max_value=1,
                ),
            },
        )

        # ── 合计行 ──
        t_cost  = sum(r["成本($)"] for r in rows)
        t_mv    = sum(r["市值($)"] for r in rows)
        t_pnl   = sum(r["盈亏($)"] for r in rows)
        t_prem  = sum(r["权利金"] for r in rows)
        t_adiv  = sum(r["年收息($)"] for r in rows)

        footer = (
            '<div style="font-family:Georgia,serif;font-size:0.9rem;color:#2D2D2D;'
            'display:flex;gap:28px;flex-wrap:wrap;margin-top:6px">'
            '<span>成本合计 <b style="font-family:\'Times New Roman\',serif">'
            + f"${t_cost:,.0f} / ¥{t_cost * usd_rmb:,.0f}" + '</b></span>'
            '<span>市值合计 <b style="font-family:\'Times New Roman\',serif">'
            + f"${t_mv:,.0f} / ¥{t_mv * usd_rmb:,.0f}" + '</b></span>'
            '<span>盈亏合计 <b style="font-family:\'Times New Roman\',serif;color:'
            + (COLORS["gain"] if t_pnl >= 0 else COLORS["loss"]) + '">'
            + f"${t_pnl:+,.0f}" + '</b></span>'
            '<span>累计权利金 <b style="font-family:\'Times New Roman\',serif">'
            + f"${t_prem:,.0f}" + '</b></span>'
            '<span>预估年收息 <b style="font-family:\'Times New Roman\',serif">'
            + f"${t_adiv:,.2f}" + '</b></span>'
            '</div>'
        )
        st.markdown(footer, unsafe_allow_html=True)
    else:
        st.caption("暂无持仓")


# ════════════════════════════════════════════════════════
#  子页面 3 ── 期权策略 (Options Wheel) — 简洁版概览
# ════════════════════════════════════════════════════════

def _sub_options(data):
    tx_raw = data["tx_raw"]
    usd_rmb = data["usd_rmb"]

    option_symbols = sorted(set(
        t["symbol"] for t in tx_raw
        if t.get("action") in OPTION_ACTIONS and t.get("symbol")
    ))

    if not option_symbols:
        st.info("暂无期权交易记录")
        return

    all_relevant = [
        t for t in tx_raw
        if t.get("symbol") in option_symbols
        and t.get("action") in (OPTION_ACTIONS | STOCK_ACTIONS)
    ]
    transactions = [dict_to_transaction(t) for t in all_relevant]
    wheel_calc = WheelCalculator(transactions)

    _heading("期权标的总览")

    overview_rows = []
    for sym in option_symbols:
        basis    = wheel_calc.calculate_adjusted_cost_basis(sym)
        premiums = wheel_calc.option_calc.get_premiums_summary(sym)
        shares   = int(basis.get("current_shares", 0))

        # 车轮周期状态
        cycle = wheel_calc.get_wheel_cycle_info(sym)
        status_map = {
            "holding": "持股中 · 卖 Call",
            "waiting": "等待接盘 · 卖 Put",
            "empty":   "无交易",
        }
        status_label = status_map.get(cycle.get("status", ""), "—")

        sym_dates = [t["datetime"][:10] for t in all_relevant if t["symbol"] == sym]
        first_date = min(sym_dates) if sym_dates else ""
        days_held  = (datetime.now() - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date else 0

        net_prem   = premiums.get("net_premium", 0)
        cost_basis = basis.get("cost_basis", 0)
        adj_cost   = basis.get("adjusted_cost", 0)

        ann_ret = 0.0
        if cost_basis > 0 and days_held > 0:
            ann_ret = (net_prem / cost_basis) * (365 / days_held) * 100

        overview_rows.append({
            "标的": stock_label(sym),
            "状态": status_label,
            "持仓(股)": shares,
            "净权利金": net_prem,
            "调整成本/股": adj_cost if shares else None,
            "年化%": ann_ret,
            "天数": days_held,
        })

    odf = pd.DataFrame(overview_rows)
    st.dataframe(odf, use_container_width=True, hide_index=True,
                 column_config={
                     "净权利金": st.column_config.NumberColumn("净权利金", format="$%,.2f"),
                     "调整成本/股": st.column_config.NumberColumn("调整成本/股", format="$%.2f"),
                     "年化%": st.column_config.NumberColumn("年化%", format="%.1f%%"),
                 })

    # ── 按标的展开详情 ──
    selected = st.selectbox("选择标的查看详情", option_symbols,
                            format_func=stock_label, key="port_opt_sel")

    basis = wheel_calc.calculate_adjusted_cost_basis(selected)
    premiums = wheel_calc.option_calc.get_premiums_summary(selected)
    shares = int(basis.get("current_shares", 0))

    net_prem   = premiums.get("net_premium", 0)
    collected  = premiums.get("total_collected", 0)
    paid       = premiums.get("total_paid", 0)
    cost_basis = basis.get("cost_basis", 0)
    adj_cost   = basis.get("adjusted_cost", 0)

    metric_row([
        ("权利金收入", f"${collected:,.2f}"),
        ("权利金支出", f"${paid:,.2f}"),
        ("净权利金",   f"${net_prem:,.2f}"),
        ("调整成本",   f"${adj_cost:.2f}/股" if shares else "—"),
        ("持仓",       f"{shares} 股"),
    ])

    # ── 成本基准变化图 ──
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
            if action in ("STO", "STO_CALL"):
                running_premium += price * qty * 100
            else:
                running_premium -= price * qty * 100
        running_fees += fees

        if running_shares > 0:
            adj = (running_stock_cost - running_premium + running_fees) / running_shares
            cost_timeline.append({"日期": dt, "成本/股": round(adj, 2),
                                  "操作": ACTION_CN.get(action, action)})

    if cost_timeline:
        _heading(f"{stock_label(selected)} 成本基准变化")
        cdf = pd.DataFrame(cost_timeline)
        fig = go.Figure(go.Scatter(
            x=cdf["日期"], y=cdf["成本/股"],
            mode="lines+markers+text",
            text=[f"${v:.2f}" for v in cdf["成本/股"]],
            textposition="top center",
            textfont=dict(size=11, family="'Times New Roman', serif"),
            line=dict(color="#2B4C7E", width=3),
            marker=dict(size=9, color="#2B4C7E",
                        line=dict(color="#F9F7F0", width=1.5)),
            hovertext=cdf["操作"],
        ))
        fig.update_layout(**plotly_layout(
            height=320,
            margin=dict(l=55, r=15, t=10, b=40),
            yaxis_title="成本/股 ($)",
        ))
        st.plotly_chart(fig, use_container_width=True, key="port_opt_cost")


# ════════════════════════════════════════════════════════
#  主入口 — 子页面切换
# ════════════════════════════════════════════════════════

def page_portfolio():
    st.markdown(
        "<h1 style='margin-bottom:4px'>投资组合</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>Portfolio · 总览趋势 / 持仓明细 / 期权策略</p>",
        unsafe_allow_html=True,
    )

    data = _load_data()
    if data is None:
        st.info("暂无投资数据，去交易日志添加吧")
        return

    if not data["holdings"]:
        st.info("暂无持仓")
        return

    usd_rmb = data["usd_rmb"]
    st.caption(f"当前汇率: 1 USD = ¥{usd_rmb:.2f} CNY")

    tab1, tab2, tab3 = st.tabs(["总览趋势", "持仓明细", "期权策略"])

    with tab1:
        _sub_overview(data)
    with tab2:
        _sub_holdings(data)
    with tab3:
        _sub_options(data)
