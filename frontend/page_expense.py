"""页面：支出与收入 Expense/Income Tracker"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from src.database_v2 import add_transaction, get_transactions

from .config import COLORS, EXPENSE_CATEGORIES
from .helpers import fetch_exchange_rates, plotly_layout, metric_row


def page_expense_tracker():
    st.title("💸 支出与收入 Tracker")
    st.caption("记录每月收支，分析消费习惯")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ── 新增记录 ──
    with st.expander("➕ 记一笔", expanded=False):
        c1, c2, c3 = st.columns(3)
        tx_type  = c1.selectbox("类型", ["EXPENSE", "INCOME"])
        amount   = c2.number_input("金额", value=0.0)
        currency = c3.selectbox("币种", ["USD", "CNY", "HKD"])

        c4, c5, c6 = st.columns(3)
        category    = c4.selectbox("分类", EXPENSE_CATEGORIES)
        subcategory = c5.text_input("子分类（可选）")
        target      = c6.text_input("对象（可选）")

        c7, c8 = st.columns(2)
        note     = c7.text_input("备注")
        date_val = c8.date_input("日期", value=datetime.now().date())

        if st.button("💾 保存"):
            add_transaction(
                datetime_str=date_val.strftime("%Y-%m-%d"),
                action=tx_type,
                quantity=1,
                price=amount,
                currency=currency,
                category="支出" if tx_type == "EXPENSE" else "收入",
                subcategory=category,
                target=target,
                note=note,
            )
            st.success("✅ 已保存！")
            st.rerun()

    # ── 月度分析 ──
    raw = get_transactions(limit=500)
    if not raw:
        st.caption("暂无记录")
        return

    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["datetime"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["amount_rmb"] = df.apply(
        lambda x: x["price"] * (
            usd_rmb if x["currency"] == "USD"
            else hkd_rmb if x["currency"] == "HKD"
            else 1
        ),
        axis=1,
    )

    months = sorted(df["month"].unique(), reverse=True)
    selected = st.selectbox("选择月份", months)
    mdf = df[df["month"] == selected]

    income  = mdf[mdf["action"] == "INCOME"]["amount_rmb"].sum()
    expense = mdf[mdf["action"] == "EXPENSE"]["amount_rmb"].sum()
    net = income - expense

    metric_row([
        ("💰 本月收入", f"¥{income:,.0f}"),
        ("💸 本月支出", f"¥{expense:,.0f}"),
        ("📊 净积累",   f"¥{net:,.0f}", f"¥{net:,.0f}"),
    ])

    left, right = st.columns(2)

    with left:
        st.subheader("📊 支出分类")
        exp_df = mdf[mdf["action"] == "EXPENSE"]
        if not exp_df.empty:
            grp = exp_df.groupby("subcategory")["amount_rmb"].sum()
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0.4, marker=dict(colors=px.colors.qualitative.Set3),
            ))
            fig.update_layout(**plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📈 收入分类")
        inc_df = mdf[mdf["action"] == "INCOME"]
        if not inc_df.empty:
            grp = inc_df.groupby("subcategory")["amount_rmb"].sum()
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0.4, marker=dict(colors=px.colors.qualitative.Pastel),
            ))
            fig.update_layout(**plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📝 本月明细")
    d = mdf[["date", "action", "subcategory", "price", "currency", "target", "note"]].copy()
    d["date"] = d["date"].dt.strftime("%Y-%m-%d")
    d.columns = ["日期", "类型", "分类", "金额", "币种", "对象", "备注"]
    st.dataframe(d, use_container_width=True, hide_index=True)
