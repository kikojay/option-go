"""页面：收支管理 — 仅日常收支，过滤投资/期权交易"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import add_transaction, get_transactions

from .config import COLORS, EXPENSE_CATEGORIES
from .helpers import fetch_exchange_rates, plotly_layout


# ── 需要过滤掉的投资/期权 action ──
_INVEST_ACTIONS = {
    "BUY", "SELL", "STO", "STO_CALL", "STC", "BTC",
    "BTO_CALL", "ASSIGNMENT", "CALLED_AWAY", "DIVIDEND",
}


def page_expense_tracker():
    st.markdown(
        "<h1 style='margin-bottom:4px'>收支管理</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>"
        "日常收入与消费记录 · 自动剔除投资/期权交易</p>",
        unsafe_allow_html=True,
    )

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ══════════════════════════════════════════════════════
    #  新增记录
    # ══════════════════════════════════════════════════════

    with st.expander("✏️ 记一笔", expanded=False):
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

        if st.button("保存", key="btn_save_expense"):
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
            st.success("已保存！")
            st.rerun()

    # ══════════════════════════════════════════════════════
    #  加载数据 & 过滤投资交易
    # ══════════════════════════════════════════════════════

    raw = get_transactions(limit=2000)
    if not raw:
        st.caption("暂无记录")
        return

    df = pd.DataFrame(raw)
    df = df[~df["action"].isin(_INVEST_ACTIONS)].copy()
    if df.empty:
        st.caption("暂无日常收支记录（投资/期权交易已自动过滤）")
        return

    df["date"] = pd.to_datetime(df["datetime"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["year"]  = df["date"].dt.year
    df["amount_rmb"] = df.apply(
        lambda x: x["price"] * (
            usd_rmb if x.get("currency") == "USD"
            else hkd_rmb if x.get("currency") == "HKD"
            else 1
        ),
        axis=1,
    )

    # ══════════════════════════════════════════════════════
    #  年度收支汇总（顶部看板）
    # ══════════════════════════════════════════════════════

    cur_year = datetime.now().year
    year_df = df[df["year"] == cur_year]
    y_income  = year_df[year_df["action"] == "INCOME"]["amount_rmb"].sum()
    y_expense = year_df[year_df["action"] == "EXPENSE"]["amount_rmb"].sum()
    y_net = y_income - y_expense

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric(f"{cur_year} 年度收入", f"¥{y_income:,.0f}")
    mc2.metric(f"{cur_year} 年度支出", f"¥{y_expense:,.0f}")
    mc3.metric(f"{cur_year} 年度净积累", f"¥{y_net:,.0f}",
               delta=f"¥{y_net:,.0f}")

    # ── 年度月度趋势图 ──
    monthly_agg = year_df.groupby(["month", "action"])["amount_rmb"].sum().unstack(fill_value=0)
    if "INCOME" not in monthly_agg.columns:
        monthly_agg["INCOME"] = 0
    if "EXPENSE" not in monthly_agg.columns:
        monthly_agg["EXPENSE"] = 0
    monthly_agg = monthly_agg.sort_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="收入", x=monthly_agg.index, y=monthly_agg["INCOME"],
        marker_color="#5B8C5A", width=0.35,
    ))
    fig.add_trace(go.Bar(
        name="支出", x=monthly_agg.index, y=monthly_agg["EXPENSE"],
        marker_color="#C0392B", width=0.35,
    ))
    net_vals = monthly_agg["INCOME"] - monthly_agg["EXPENSE"]
    fig.add_trace(go.Scatter(
        name="净额", x=monthly_agg.index, y=net_vals,
        mode="lines+markers",
        line=dict(color="#2B4C7E", width=3),
        marker=dict(size=7, color="#2B4C7E"),
    ))
    fig.update_layout(**plotly_layout(
        height=320,
        barmode="group",
        margin=dict(l=55, r=15, t=30, b=40),
        xaxis_title="月份",
        yaxis_title="金额 (¥)",
    ))
    st.plotly_chart(fig, use_container_width=True, key="expense_annual_trend")

    st.markdown('<hr style="border:none;border-top:2px solid #2D2D2D;margin:1.2rem 0">',
                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    #  月度筛选
    # ══════════════════════════════════════════════════════

    months = sorted(df["month"].unique(), reverse=True)
    cur_month = datetime.now().strftime("%Y-%m")
    default_idx = months.index(cur_month) if cur_month in months else 0
    selected = st.selectbox("选择月份", months, index=default_idx)
    mdf = df[df["month"] == selected]

    income  = mdf[mdf["action"] == "INCOME"]["amount_rmb"].sum()
    expense = mdf[mdf["action"] == "EXPENSE"]["amount_rmb"].sum()
    net = income - expense

    mc4, mc5, mc6 = st.columns(3)
    mc4.metric("本月收入", f"¥{income:,.0f}")
    mc5.metric("本月支出", f"¥{expense:,.0f}")
    mc6.metric("本月净额", f"¥{net:,.0f}", delta=f"¥{net:,.0f}")

    # ── 分类饼图 ──
    left, right = st.columns(2)

    with left:
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>支出分类</h3>",
            unsafe_allow_html=True,
        )
        exp_df = mdf[mdf["action"] == "EXPENSE"]
        if not exp_df.empty:
            grp = exp_df.groupby("subcategory")["amount_rmb"].sum().sort_values(ascending=False)
            palette = ["#2B4C7E", "#5B8C5A", "#D4A017", "#C0392B",
                       "#6C3483", "#48B4A0", "#D4783A", "#7E8C6E"]
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0,
                marker=dict(colors=palette[:len(grp)],
                            line=dict(color="#F9F7F0", width=2)),
                textinfo="label+percent",
                textfont=dict(size=13, family="'Times New Roman', Georgia, serif",
                              color="#FFFFFF"),
                insidetextorientation="radial",
                hovertemplate="%{label}<br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            fig.update_layout(**plotly_layout(height=320, showlegend=False,
                                              margin=dict(l=5, r=5, t=10, b=10)))
            st.plotly_chart(fig, use_container_width=True, key="expense_cat_pie")
        else:
            st.caption("本月无支出")

    with right:
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>收入分类</h3>",
            unsafe_allow_html=True,
        )
        inc_df = mdf[mdf["action"] == "INCOME"]
        if not inc_df.empty:
            grp = inc_df.groupby("subcategory")["amount_rmb"].sum().sort_values(ascending=False)
            palette2 = ["#5B8C5A", "#48B4A0", "#2B4C7E", "#D4A017",
                        "#6C3483", "#D4783A", "#C0392B", "#937B6A"]
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0,
                marker=dict(colors=palette2[:len(grp)],
                            line=dict(color="#F9F7F0", width=2)),
                textinfo="label+percent",
                textfont=dict(size=13, family="'Times New Roman', Georgia, serif",
                              color="#FFFFFF"),
                insidetextorientation="radial",
                hovertemplate="%{label}<br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            fig.update_layout(**plotly_layout(height=320, showlegend=False,
                                              margin=dict(l=5, r=5, t=10, b=10)))
            st.plotly_chart(fig, use_container_width=True, key="income_cat_pie")
        else:
            st.caption("本月无收入")

    # ── 月度明细表 ──
    st.markdown(
        "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px;margin-top:1rem'>本月明细</h3>",
        unsafe_allow_html=True,
    )
    d = mdf[["date", "action", "subcategory", "price", "currency", "target", "note"]].copy()
    d["date"] = d["date"].dt.strftime("%Y-%m-%d")
    d["action"] = d["action"].map({"INCOME": "收入", "EXPENSE": "支出"}).fillna(d["action"])
    # 币种直接拼到金额后面，节省水平空间
    d["金额"] = d.apply(
        lambda r: f"{r['price']:,.2f} {r['currency']}", axis=1,
    )
    d = d[["date", "action", "subcategory", "金额", "target", "note"]]
    d.columns = ["日期", "类型", "分类", "金额", "对象", "备注"]
    st.dataframe(d, use_container_width=True, hide_index=True)
