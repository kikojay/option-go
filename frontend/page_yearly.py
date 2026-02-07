"""页面：年度汇总 Yearly Summary"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import update_yearly_summary, get_yearly_summary

from .config import COLORS
from .helpers import plotly_layout


def page_yearly_summary():
    st.markdown(
        "<h1 style='margin-bottom:4px'>年度汇总</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>Yearly Summary · 收入 / 扣缴 / 理财总览</p>",
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════
    #  年度数据（先加载，图表在上方）
    # ══════════════════════════════════════════════════════

    summaries = get_yearly_summary()

    if summaries:
        df = pd.DataFrame(summaries)
        df["year_str"] = df["year"].astype(str) + "年"

        # ── 收入对比 ──
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>收入对比</h3>",
            unsafe_allow_html=True,
        )

        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            name="税前收入", x=df["year_str"], y=df["pre_tax_income"] / 10000,
            marker_color=COLORS["primary"], width=0.16,
            marker_line=dict(color="#1A324F", width=1),
        ))
        fig1.add_trace(go.Bar(
            name="税后收入", x=df["year_str"], y=df["post_tax_income"] / 10000,
            marker_color=COLORS["secondary"], width=0.16,
            marker_line=dict(color="#3A6A38", width=1),
        ))
        fig1.add_trace(go.Scatter(
            name="税后趋势", x=df["year_str"], y=df["post_tax_income"] / 10000,
            mode="lines+markers", yaxis="y",
            line=dict(color="#6C3483", width=2.5, dash="dot"),
            marker=dict(size=7, color="#6C3483",
                        line=dict(color="#F9F7F0", width=1.5)),
            hovertemplate="%{x}: %{y:.1f} 万元<extra></extra>",
        ))
        fig1.update_layout(**plotly_layout(
            height=310,
            barmode="group",
            bargroupgap=0.15,
            yaxis_title="金额（万元）",
            margin=dict(l=55, r=15, t=10, b=40),
            hovermode="x unified",
        ))
        fig1.update_yaxes(ticksuffix=" 万")
        st.plotly_chart(fig1, use_container_width=True, key="yr_income")

        # ── 扣缴明细 ──
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>扣缴明细</h3>",
            unsafe_allow_html=True,
        )

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="五险一金", x=df["year_str"], y=df["social_insurance"] / 10000,
            marker_color=COLORS["danger"], width=0.16,
            marker_line=dict(color="#7A1D15", width=1),
        ))
        fig2.add_trace(go.Bar(
            name="个税", x=df["year_str"], y=df["income_tax"] / 10000,
            marker_color=COLORS["warning"], width=0.16,
            marker_line=dict(color="#9A760E", width=1),
        ))
        total_deduct = (df["social_insurance"] + df["income_tax"]) / 10000
        fig2.add_trace(go.Scatter(
            name="合计扣缴", x=df["year_str"], y=total_deduct,
            mode="lines+markers", yaxis="y",
            line=dict(color="#6C3483", width=2.5, dash="dot"),
            marker=dict(size=7, color="#6C3483",
                        line=dict(color="#F9F7F0", width=1.5)),
            hovertemplate="%{x}: %{y:.1f} 万元<extra></extra>",
        ))
        fig2.update_layout(**plotly_layout(
            height=310,
            bargroupgap=0.15,
            yaxis_title="金额（万元）",
            margin=dict(l=55, r=15, t=10, b=40),
            hovermode="x unified",
        ))
        fig2.update_yaxes(ticksuffix=" 万")
        st.plotly_chart(fig2, use_container_width=True, key="yr_deduct")

        st.markdown('<hr style="border:none;border-top:1px solid #2D2D2D;margin:1rem 0">',
                    unsafe_allow_html=True)

        # ── 明细表 ──
        display = df[["year", "pre_tax_income", "social_insurance", "income_tax",
                       "post_tax_income", "investment_income", "note"]].copy()
        display.columns = ["年份", "税前收入", "五险一金", "个人所得税",
                            "税后收入", "理财收入", "备注"]
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "税前收入": st.column_config.NumberColumn("税前收入", format="¥%,.0f"),
                "五险一金": st.column_config.NumberColumn("五险一金", format="¥%,.0f"),
                "个人所得税": st.column_config.NumberColumn("个人所得税", format="¥%,.0f"),
                "税后收入": st.column_config.NumberColumn("税后收入", format="¥%,.0f"),
                "理财收入": st.column_config.NumberColumn("理财收入", format="¥%,.0f"),
            },
        )

        # ── 底部总汇总 ──
        sum_pre = df["pre_tax_income"].sum()
        sum_post = df["post_tax_income"].sum()
        sum_social = df["social_insurance"].sum()
        sum_tax = df["income_tax"].sum()
        sum_invest = df["investment_income"].sum()
        n_years = len(df)

        footer_html = (
            '<hr style="border:none;border-top:2px solid #2D2D2D;margin:1.5rem 0 0.8rem 0">'
            '<div style="font-family:Georgia,serif;color:#2D2D2D;text-align:center">'
            '<div style="font-size:1.1rem;font-weight:700;margin-bottom:8px">'
            + str(n_years) + ' 年累计汇总</div>'
            '<div style="display:flex;justify-content:center;gap:32px;flex-wrap:wrap;font-size:0.95rem">'
            '<span>税前收入 <b style="font-family:\'Times New Roman\',serif">¥'
            + f"{sum_pre:,.0f}" + '</b></span>'
            '<span>税后收入 <b style="font-family:\'Times New Roman\',serif">¥'
            + f"{sum_post:,.0f}" + '</b></span>'
            '<span>五险一金 <b style="font-family:\'Times New Roman\',serif">¥'
            + f"{sum_social:,.0f}" + '</b></span>'
            '<span>个人所得税 <b style="font-family:\'Times New Roman\',serif">¥'
            + f"{sum_tax:,.0f}" + '</b></span>'
            '<span>理财收入 <b style="font-family:\'Times New Roman\',serif">¥'
            + f"{sum_invest:,.0f}" + '</b></span>'
            '</div></div>'
        )
        st.markdown(footer_html, unsafe_allow_html=True)

    else:
        st.caption("暂无年度数据，请先添加。")

    # ══════════════════════════════════════════════════════
    #  添加 / 更新 年度数据（放在底部）
    # ══════════════════════════════════════════════════════

    st.markdown('<hr style="border:none;border-top:1px solid #C8C3B5;margin:1.5rem 0 0.5rem 0">',
                unsafe_allow_html=True)

    with st.expander("添加 / 更新年度数据", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        year    = c1.number_input("年份", 2020, 2030, datetime.now().year)
        pre_tax = c2.number_input("税前收入", value=0.0)
        social  = c3.number_input("五险一金", value=0.0)
        tax     = c4.number_input("个人所得税", value=0.0)

        c5, c6 = st.columns(2)
        invest = c5.number_input("理财收入", value=0.0)
        note   = c6.text_input("备注")

        if st.button("保存", key="btn_yr_save"):
            update_yearly_summary(year, pre_tax, social, tax, invest, note)
            st.success("已保存！")
            st.rerun()
