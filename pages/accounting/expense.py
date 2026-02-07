"""日常收支页面 — 个人收入 · 支出 · 类别分析"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from ui import UI, plotly_layout
from services import ExpenseService
from config import EXPENSE_SUBCATEGORIES
import db


def render():
    UI.inject_css()
    UI.header("日常收支", "个人收入 · 支出 · 类别分析")

    usd_rmb = st.session_state.usd_rmb
    hkd_rmb = st.session_state.hkd_rmb

    # 加载数据
    df = ExpenseService.load(usd_rmb, hkd_rmb)
    if df is None or df.empty:
        _add_form()
        return

    years = sorted(df["year"].unique(), reverse=True)
    year = st.selectbox("年份", years, key="exp_year")

    # 1. 年度指标
    ys = ExpenseService.year_summary(df, year)
    UI.metric_row([
        ("年收入", f"¥{ys['income']:,.0f}"),
        ("年支出", f"¥{ys['expense']:,.0f}"),
        ("年净额", f"¥{ys['net']:,.0f}"),
        ("储蓄率", f"{ys['save_rate']:.1f}%"),
    ])

    # 2. 月度趋势
    UI.sub_heading("月度趋势")
    agg = ExpenseService.monthly_trend(df, year)
    fig = go.Figure()
    if "EXPENSE" in agg.columns:
        fig.add_trace(go.Bar(
            x=agg.index, y=agg["EXPENSE"], name="支出",
            marker_color="#C0392B", width=0.3))
    if "INCOME" in agg.columns:
        fig.add_trace(go.Bar(
            x=agg.index, y=agg["INCOME"], name="收入",
            marker_color="#2B4C7E", width=0.3))
    if "NET" in agg.columns:
        fig.add_trace(go.Scatter(
            x=agg.index, y=agg["NET"], name="净额",
            mode="lines+markers",
            line=dict(color="#D4A017", width=2.5)))
    fig.update_layout(**plotly_layout(height=350, hovermode="x unified"))
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})

    # 3. 月份选择 -> 分类饼图 + 明细
    months = sorted(df[df["year"] == year]["month"].unique(), reverse=True)
    month = st.selectbox("月份", months, key="exp_month") if months else None

    if month:
        ms = ExpenseService.month_summary(df, month)
        UI.metric_row([
            ("月收入", f"¥{ms['income']:,.0f}"),
            ("月支出", f"¥{ms['expense']:,.0f}"),
            ("月净额", f"¥{ms['net']:,.0f}"),
        ])

        exp_s, inc_s = ExpenseService.category_groups(df, month)
        c1, c2 = st.columns(2)
        with c1:
            if not exp_s.empty:
                UI.sub_heading("支出分类")
                fig = go.Figure(go.Pie(
                    labels=exp_s.index.tolist(),
                    values=exp_s.values.tolist(), hole=0.35))
                fig.update_layout(**plotly_layout(height=300, showlegend=True))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})
        with c2:
            if not inc_s.empty:
                UI.sub_heading("收入分类")
                fig = go.Figure(go.Pie(
                    labels=inc_s.index.tolist(),
                    values=inc_s.values.tolist(), hole=0.35))
                fig.update_layout(**plotly_layout(height=300, showlegend=True))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

        with UI.expander("当月明细", expanded=False):
            detail = ExpenseService.detail(df, month)
            display = detail.rename(columns={
                "date": "日期",
                "action_label": "类型",
                "subcategory": "分类",
                "amount_display": "金额",
                "note": "备注",
            })
            UI.table(display, max_height=400)

    _add_form()


def _add_form():
    """收支录入表单。"""
    with UI.expander("添加收支记录", expanded=False):
        c1, c2, c3 = st.columns(3)
        action = c1.selectbox("类型", ["INCOME", "EXPENSE"], key="ef_act",
                              format_func=lambda a: "收入" if a == "INCOME" else "支出")
        sub = c2.selectbox("分类", EXPENSE_SUBCATEGORIES, key="ef_sub")
        cur = c3.selectbox("币种", ["CNY", "USD", "HKD"], key="ef_cur")

        c4, c5 = st.columns(2)
        price = c4.number_input("金额", min_value=0.0, step=10.0, key="ef_price")
        target = c5.text_input("对象", key="ef_target")
        note = st.text_input("备注", key="ef_note")

        if st.button("保存", key="btn_add_exp", use_container_width=True):
            db.transactions.add(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action, symbol=target or sub,
                quantity=1, price=price, fees=0, currency=cur,
                subcategory=sub, note=note)
            st.rerun()
