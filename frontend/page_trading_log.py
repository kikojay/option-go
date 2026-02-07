"""页面：交易日志 Trading Log"""
import streamlit as st
import pandas as pd
from datetime import datetime

from src.database_v2 import add_transaction, get_transactions

from .config import COLORS, ACTION_CN, TRADE_ACTIONS
from .helpers import (
    fetch_exchange_rates, stock_label, metric_row,
)


def page_trading_log():
    st.markdown(
        "<h1 style='margin-bottom:4px'>📝 交易日志</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>记录每笔投资交易，支持筛选和统计</p>",
        unsafe_allow_html=True,
    )

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ── 新增交易 ──
    with st.expander("➕ 添加交易", expanded=False):
        c1, c2, c3 = st.columns(3)
        symbol   = c1.text_input("标的代码", placeholder="AAPL").upper()
        action   = c2.selectbox("操作", TRADE_ACTIONS)
        date_val = c3.date_input("日期", value=datetime.now().date())

        c4, c5, c6 = st.columns(3)
        quantity = c4.number_input("数量(股/张)", value=100)
        price    = c5.number_input("价格/权利金", value=100.0)
        fees     = c6.number_input("手续费", value=0.0)

        c7, c8 = st.columns(2)
        currency = c7.selectbox("币种", ["USD", "CNY", "HKD"])
        note     = c8.text_input("备注（可选）")

        if st.button("💾 保存交易"):
            action_code = action.split()[0]
            add_transaction(
                datetime_str=date_val.strftime("%Y-%m-%d"),
                action=action_code,
                symbol=symbol,
                quantity=quantity,
                price=price,
                fees=fees,
                currency=currency,
                category="投资",
                note=note,
            )
            st.success("✅ 已保存！")
            st.rerun()

    # ── 交易列表 ──
    tx_raw = get_transactions(category="投资", limit=500)
    if not tx_raw:
        st.caption("暂无交易记录")
        return

    df = pd.DataFrame(tx_raw)
    df["date"] = pd.to_datetime(df["datetime"])

    # 计算实际金额（期权 ×100）
    option_actions = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}

    def _real_amount(row):
        p, q = row["price"], row["quantity"]
        mult = 100 if row["action"] in option_actions else 1
        rate = (
            usd_rmb if row["currency"] == "USD"
            else hkd_rmb if row["currency"] == "HKD"
            else 1
        )
        return p * q * mult * rate

    df["amount_rmb"] = df.apply(_real_amount, axis=1)

    # 筛选器
    f1, f2 = st.columns(2)
    sym_options = sorted(df["symbol"].dropna().unique().tolist())
    sym_labels = {s: stock_label(s) for s in sym_options}
    sym_filter = f1.selectbox(
        "筛选标的",
        ["全部"] + [
            f"{s} {sym_labels[s]}" if sym_labels[s] != s else s
            for s in sym_options
        ],
    )
    act_labels = sorted(df["action"].unique().tolist())
    act_filter = f2.selectbox(
        "筛选操作",
        ["全部"] + [f"{a} {ACTION_CN.get(a, a)}" for a in act_labels],
    )

    filtered = df.copy()
    if sym_filter != "全部":
        sym_code = sym_filter.split()[0]
        filtered = filtered[filtered["symbol"] == sym_code]
    if act_filter != "全部":
        act_code = act_filter.split()[0]
        filtered = filtered[filtered["action"] == act_code]

    buy_total = filtered[filtered["action"].isin(["BUY", "ASSIGNMENT"])]["amount_rmb"].sum()
    sell_total = filtered[filtered["action"].isin(["SELL", "CALLED_AWAY"])]["amount_rmb"].sum()
    option_income = filtered[filtered["action"].isin(["STO", "STO_CALL"])]["amount_rmb"].sum()
    option_expense = filtered[filtered["action"].isin(["STC", "BTC", "BTO_CALL"])]["amount_rmb"].sum()
    fee_total = filtered["fees"].sum() * usd_rmb

    metric_row([
        ("💵 股票买入",   f"¥{buy_total:,.0f}"),
        ("💴 股票卖出",   f"¥{sell_total:,.0f}"),
        ("📈 权利金收入", f"¥{option_income:,.0f}"),
        ("📉 权利金支出", f"¥{option_expense:,.0f}"),
        ("💸 手续费",     f"¥{fee_total:,.0f}"),
    ])

    st.subheader("📋 交易明细")
    d = filtered[["date", "symbol", "action", "quantity", "price", "fees", "currency", "amount_rmb"]].copy()
    d["date"]   = d["date"].dt.strftime("%Y-%m-%d")
    d["symbol"] = d["symbol"].map(stock_label)
    d["action"] = d["action"].map(lambda a: ACTION_CN.get(a, a))
    d.columns = ["日期", "标的", "操作", "数量", "单价", "手续费", "币种", "金额(RMB)"]
    st.dataframe(d, use_container_width=True, hide_index=True)
