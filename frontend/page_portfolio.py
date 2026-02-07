"""页面：投资组合 Portfolio — 三子页面（总览趋势 / 持仓明细 / 期权策略）"""
import streamlit as st
import streamlit.components.v1 as stc
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_transactions, get_all_snapshots, add_transaction

from api.stock_data import get_batch_prices
from api.stock_names import get_stock_name
from .config import COLORS, ACTION_CN, ACTION_LABELS
from .helpers import (
    fetch_exchange_rates, dict_to_transaction,
    plotly_layout, metric_row, stock_label,
)

# 延迟导入避免循环
_CALC_IMPORTED = False
PortfolioCalculator = None
WheelCalculator = None

def _ensure_calcs():
    global _CALC_IMPORTED, PortfolioCalculator, WheelCalculator
    if not _CALC_IMPORTED:
        from src import PortfolioCalculator as PC, WheelCalculator as WC
        PortfolioCalculator = PC
        WheelCalculator = WC
        _CALC_IMPORTED = True


# ── helpers ──

OPTION_ACTIONS = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}
STOCK_ACTIONS  = {"BUY", "SELL", "ASSIGNMENT", "CALLED_AWAY"}
CAPITAL_ACTIONS = {"DEPOSIT", "WITHDRAW"}


def _heading(title: str):
    st.markdown(
        "<h3 style='color:#1e293b;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px'>" + title + "</h3>",
        unsafe_allow_html=True,
    )


def _safe_html(html_str: str, height: int = 200):
    """安全渲染 HTML，使用 st.components.v1.html 避免标签泄露"""
    stc.html(html_str, height=height, scrolling=False)


# ════════════════════════════════════════════════════════
#  公共数据加载（缓存在 session_state 避免重复查询）
# ════════════════════════════════════════════════════════

def _load_data():
    _ensure_calcs()
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

    # 加载入金/出金记录
    all_tx = get_transactions(limit=5000)
    capital_flows = [
        t for t in all_tx
        if t.get("action") in CAPITAL_ACTIONS
    ]

    return {
        "rates": rates,
        "usd_rmb": usd_rmb,
        "tx_raw": tx_raw,
        "transactions": transactions,
        "calc": calc,
        "summary": summary,
        "holdings": holdings,
        "live_prices": live_prices,
        "capital_flows": capital_flows,
    }


# ════════════════════════════════════════════════════════
#  子页面 1 ── 总览趋势 (Performance)
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

    # ── 入金/出金管理 ──
    with st.expander("💰 入金/出金记录（影响收益率计算）", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        dep_type = c1.selectbox("类型", ["DEPOSIT", "WITHDRAW"],
                                format_func=lambda x: "入金" if x == "DEPOSIT" else "出金",
                                key="dep_type")
        dep_amount = c2.number_input("金额 (USD)", value=0.0, step=100.0, key="dep_amount")
        dep_date = c3.date_input("日期", value=datetime.now().date(), key="dep_date")
        dep_note = c4.text_input("备注", placeholder="例: 追加资金", key="dep_note")

        if st.button("保存", key="btn_save_deposit"):
            if dep_amount > 0:
                add_transaction(
                    datetime_str=dep_date.strftime("%Y-%m-%d"),
                    action=dep_type,
                    quantity=1,
                    price=dep_amount,
                    currency="USD",
                    category="资金流动",
                    note=dep_note or ("入金" if dep_type == "DEPOSIT" else "出金"),
                )
                st.success("已保存！")
                st.rerun()
            else:
                st.error("金额必须大于 0")

        # 显示历史入金/出金
        capital_flows = data.get("capital_flows", [])
        if capital_flows:
            cf_df = pd.DataFrame(capital_flows)
            cf_df = cf_df[cf_df["action"].isin(CAPITAL_ACTIONS)]
            if not cf_df.empty:
                cf_display = cf_df[["datetime", "action", "price", "note"]].copy()
                cf_display["datetime"] = pd.to_datetime(cf_display["datetime"]).dt.strftime("%Y-%m-%d")
                cf_display["action"] = cf_display["action"].map({"DEPOSIT": "入金", "WITHDRAW": "出金"})
                cf_display.columns = ["日期", "类型", "金额(USD)", "备注"]
                st.dataframe(cf_display, use_container_width=True, hide_index=True,
                             column_config={
                                 "金额(USD)": st.column_config.NumberColumn("金额(USD)", format="$%,.0f"),
                             })

    # ── 总资产走势（从快照数据） ──
    _heading("总资产增长曲线")

    snapshots = get_all_snapshots()
    if snapshots:
        sdf = pd.DataFrame(snapshots)
        sdf["date_parsed"] = pd.to_datetime(sdf["date"])
        sdf = sdf.sort_values("date_parsed")

        sdf["total_usd"] = sdf["total_assets_usd"]
        sdf["日期"] = sdf["date_parsed"].dt.strftime("%Y-%m-%d")

        # ── 入金/出金：计算累计净入金 ──
        capital_flows = data.get("capital_flows", [])
        if capital_flows:
            dep_records = []
            running_deposit = 0.0
            for cf in sorted(capital_flows, key=lambda x: x["datetime"]):
                act = cf.get("action", "")
                amt = cf.get("price", 0)
                if act == "DEPOSIT":
                    running_deposit += amt
                elif act == "WITHDRAW":
                    running_deposit -= amt
                dep_records.append({"date": cf["datetime"][:10], "deposit": running_deposit})

            if dep_records:
                dep_df = pd.DataFrame(dep_records).drop_duplicates(subset="date", keep="last")
                dep_df["date_parsed"] = pd.to_datetime(dep_df["date"])
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
        else:
            # 无入金记录 → 用 BUY+ASSIGNMENT 估算本金
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
            name="真实收益", x=merged["日期"], y=merged["gain"],
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
        t_mdiv  = sum(r["月分红($)"] for r in rows)

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
            '<span>预估月分红 <b style="font-family:\'Times New Roman\',serif;color:#5B8C5A">'
            + f"${t_mdiv:,.2f}" + '</b></span>'
            '</div>'
        )
        st.markdown(footer, unsafe_allow_html=True)
    else:
        st.caption("暂无持仓")


# ════════════════════════════════════════════════════════
#  子页面 3 ── 期权策略 (Options Wheel) — 简洁版概览
# ════════════════════════════════════════════════════════

def _sub_options(data):
    _ensure_calcs()
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
        and t.get("action") in (OPTION_ACTIONS | STOCK_ACTIONS | {"DIVIDEND"})
    ]
    transactions = [dict_to_transaction(t) for t in all_relevant]
    wheel_calc = WheelCalculator(transactions)

    _heading("期权标的总览")

    overview_rows = []
    for sym in option_symbols:
        basis    = wheel_calc.calculate_adjusted_cost_basis(sym)
        premiums = wheel_calc.option_calc.get_premiums_summary(sym)
        shares   = int(basis.get("current_shares", 0))

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

        # 累计分红
        sym_dividends = sum(
            t.get("price", 0) * t.get("quantity", 1)
            for t in all_relevant
            if t.get("symbol") == sym and t.get("action") == "DIVIDEND"
        )

        # 回本预测（新公式: (原始成本 - 累计权利金 - 累计分红) / 每周平均权利金）
        sym_option_txs = [
            t for t in all_relevant
            if t["symbol"] == sym and t.get("action") in OPTION_ACTIONS
        ]
        if sym_option_txs and cost_basis > 0:
            opt_dates = [t["datetime"][:10] for t in sym_option_txs]
            first_opt = datetime.strptime(min(opt_dates), "%Y-%m-%d")
            last_opt = datetime.strptime(max(opt_dates), "%Y-%m-%d")
            weeks_active = max((last_opt - first_opt).days / 7, 1)
            avg_weekly_prem = net_prem / weeks_active
            remaining = cost_basis - net_prem - sym_dividends
            weeks_to_zero = remaining / avg_weekly_prem if avg_weekly_prem > 0 else float("inf")
        else:
            avg_weekly_prem = 0
            weeks_to_zero = float("inf")

        overview_rows.append({
            "标的": stock_label(sym),
            "状态": status_label,
            "持仓(股)": shares,
            "净权利金": net_prem,
            "累计分红": sym_dividends,
            "调整成本/股": adj_cost if shares else None,
            "年化%": ann_ret,
            "回本(周)": round(weeks_to_zero, 1) if weeks_to_zero != float("inf") else None,
            "天数": days_held,
        })

    odf = pd.DataFrame(overview_rows)
    st.dataframe(odf, use_container_width=True, hide_index=True,
                 column_config={
                     "净权利金": st.column_config.NumberColumn("净权利金", format="$%,.2f"),
                     "累计分红": st.column_config.NumberColumn("累计分红", format="$%,.2f"),
                     "调整成本/股": st.column_config.NumberColumn("调整成本/股", format="$%.2f"),
                     "年化%": st.column_config.NumberColumn("年化%", format="%.1f%%"),
                     "回本(周)": st.column_config.NumberColumn("预计回本(周)", format="%.1f"),
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

    # 累计分红
    sel_dividends = sum(
        t.get("price", 0) * t.get("quantity", 1)
        for t in all_relevant
        if t.get("symbol") == selected and t.get("action") == "DIVIDEND"
    )

    metric_row([
        ("权利金收入", f"${collected:,.2f}"),
        ("权利金支出", f"${paid:,.2f}"),
        ("净权利金",   f"${net_prem:,.2f}"),
        ("累计分红",   f"${sel_dividends:,.2f}"),
        ("调整成本",   f"${adj_cost:.2f}/股" if shares else "—"),
        ("持仓",       f"{shares} 股"),
    ])

    # ── 回本预测面板 ──
    if shares > 0 and cost_basis > 0:
        sel_opt_txs = [
            t for t in all_relevant
            if t["symbol"] == selected and t.get("action") in OPTION_ACTIONS
        ]
        if sel_opt_txs:
            opt_dates = [t["datetime"][:10] for t in sel_opt_txs]
            first_opt = datetime.strptime(min(opt_dates), "%Y-%m-%d")
            last_opt = datetime.strptime(max(opt_dates), "%Y-%m-%d")
            weeks_active = max((last_opt - first_opt).days / 7, 1)
            avg_weekly_prem = net_prem / weeks_active

            remaining_cost = cost_basis - net_prem - sel_dividends
            if avg_weekly_prem > 0:
                weeks_to_zero = remaining_cost / avg_weekly_prem
                progress = min((net_prem + sel_dividends) / cost_basis, 1.0)

                st.markdown('<hr style="border:none;border-top:1px solid #C8C3B5;margin:0.8rem 0">',
                            unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                c1.metric("每周均权利金", f"${avg_weekly_prem:,.2f}")
                c2.metric("剩余成本", f"${remaining_cost:,.0f}")
                c3.metric("预计回本", f"{weeks_to_zero:.0f} 周 ({weeks_to_zero / 4.33:.0f} 月)")

                st.progress(progress, text=f"回本进度 {progress * 100:.1f}%  "
                            f"(权利金 ${net_prem:,.0f} + 分红 ${sel_dividends:,.0f}) / 成本 ${cost_basis:,.0f}")

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
