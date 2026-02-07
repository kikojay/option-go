"""页面：年度汇总 Yearly Summary"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import update_yearly_summary, get_yearly_summary

from .config import COLORS
from .helpers import plotly_layout


def page_yearly_summary():
    st.title("📆 年度汇总 Yearly Summary")

    with st.expander("➕ 添加/更新年度数据", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        year    = c1.number_input("年份", 2020, 2030, datetime.now().year)
        pre_tax = c2.number_input("税前收入", value=0.0)
        social  = c3.number_input("五险一金", value=0.0)
        tax     = c4.number_input("个人所得税", value=0.0)

        c5, c6 = st.columns(2)
        invest = c5.number_input("理财收入", value=0.0)
        note   = c6.text_input("备注")

        if st.button("💾 保存"):
            update_yearly_summary(year, pre_tax, social, tax, invest, note)
            st.success("✅ 已保存！")
            st.rerun()

    summaries = get_yearly_summary()
    if not summaries:
        st.caption("暂无年度数据")
        return

    df = pd.DataFrame(summaries)

    left, right = st.columns(2)
    with left:
        st.subheader("📈 收入对比")
        fig = go.Figure([
            go.Bar(
                name="税前", x=df["year"], y=df["pre_tax_income"],
                marker_color=COLORS["primary"],
            ),
            go.Bar(
                name="税后", x=df["year"], y=df["post_tax_income"],
                marker_color=COLORS["secondary"],
            ),
        ])
        fig.update_layout(**plotly_layout(barmode="group"))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📊 扣缴明细")
        fig = go.Figure([
            go.Bar(
                name="五险一金", x=df["year"], y=df["social_insurance"],
                marker_color=COLORS["danger"],
            ),
            go.Bar(
                name="个税", x=df["year"], y=df["income_tax"],
                marker_color=COLORS["warning"],
            ),
        ])
        fig.update_layout(**plotly_layout())
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True, hide_index=True)
