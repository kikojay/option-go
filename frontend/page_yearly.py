"""页面：年度汇总 Yearly Summary（修复版）"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import update_yearly_summary, get_yearly_summary

from .config import COLORS
from .helpers import plotly_layout


def page_yearly_summary():
    # 顶部标题
    st.markdown(
        "<h1 style='margin-bottom:4px; font-family:Georgia, serif;'>年度汇总</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>Yearly Summary · 收入 / 扣缴 / 理财总览</p>"
        "<hr style='border:none;border-top:2px solid #2D2D2D;margin-top:0;margin-bottom:20px'>",
        unsafe_allow_html=True,
    )

    # 年度数据加载
    summaries = get_yearly_summary()

    if summaries:
        df = pd.DataFrame(summaries)
        df["年份"] = df["year"].astype(str)

        # ── 收入对比图表 ──
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>收入对比</h3>",
            unsafe_allow_html=True,
        )

        fig1 = go.Figure()
        
        # 细柱状图：税前 + 税后
        fig1.add_trace(go.Bar(
            name="税前收入",
            x=df["年份"],
            y=df["pre_tax_income"] / 10000,
            marker_color="#2B4C7E",
            width=0.3,
            hovertemplate="年份: %{x}<br>税前: ¥%{y:.2f}万<extra></extra>"
        ))
        
        fig1.add_trace(go.Bar(
            name="税后收入",
            x=df["年份"],
            y=df["post_tax_income"] / 10000,
            marker_color="#5B8AC5",
            width=0.3,
            hovertemplate="年份: %{x}<br>税后: ¥%{y:.2f}万<extra></extra>"
        ))
        
        # 叠加趋势线
        fig1.add_trace(go.Scatter(
            name="税后趋势",
            x=df["年份"],
            y=df["post_tax_income"] / 10000,
            mode="lines+markers",
            line=dict(color="#6C3483", width=2.5),
            marker=dict(size=8, color="#6C3483", line=dict(color="#F9F7F0", width=1.5)),
            hovertemplate="年份: %{x}<br>趋势: ¥%{y:.2f}万<extra></extra>"
        ))

        fig1.update_layout(**plotly_layout(
            height=340,
            barmode="group",
            xaxis_title="年份",
            yaxis_title="金额（万元）",
            margin=dict(l=55, r=15, t=15, b=40),
            hovermode="x unified"
        ))
        fig1.update_yaxes(ticksuffix=" 万")
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

        # ── 扣缴明细图表 ──
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>扣缴明细</h3>",
            unsafe_allow_html=True,
        )

        fig2 = go.Figure()
        
        # 细柱状图：五险一金 + 个税
        fig2.add_trace(go.Bar(
            name="五险一金",
            x=df["年份"],
            y=df["social_insurance"] / 10000,
            marker_color="#E74C3C",
            width=0.3,
            hovertemplate="年份: %{x}<br>五险一金: ¥%{y:.2f}万<extra></extra>"
        ))
        
        fig2.add_trace(go.Bar(
            name="个人所得税",
            x=df["年份"],
            y=df["income_tax"] / 10000,
            marker_color="#F8B88B",
            width=0.3,
            hovertemplate="年份: %{x}<br>个税: ¥%{y:.2f}万<extra></extra>"
        ))
        
        # 合计扣缴趋势线
        total_deduct = (df["social_insurance"] + df["income_tax"]) / 10000
        fig2.add_trace(go.Scatter(
            name="合计扣缴",
            x=df["年份"],
            y=total_deduct,
            mode="lines+markers",
            line=dict(color="#8B4513", width=2.5),
            marker=dict(size=8, color="#8B4513", line=dict(color="#F9F7F0", width=1.5)),
            hovertemplate="年份: %{x}<br>合计: ¥%{y:.2f}万<extra></extra>"
        ))

        fig2.update_layout(**plotly_layout(
            height=340,
            barmode="group",
            xaxis_title="年份",
            yaxis_title="金额（万元）",
            margin=dict(l=55, r=15, t=15, b=40),
            hovermode="x unified"
        ))
        fig2.update_yaxes(ticksuffix=" 万")
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

        st.markdown('<hr style="border:none;border-top:1px solid #2D2D2D;margin:1rem 0">',
                    unsafe_allow_html=True)

        # ── 详细数据表 ──
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
            "padding-bottom:4px'>详细数据</h3>",
            unsafe_allow_html=True,
        )

        display = df[["year", "pre_tax_income", "social_insurance", "income_tax",
                       "post_tax_income", "investment_income", "note"]].copy()
        display.columns = ["年份", "税前收入", "五险一金", "个人所得税",
                            "税后收入", "理财收入", "备注"]
        
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "年份": st.column_config.TextColumn("年份"),
                "税前收入": st.column_config.NumberColumn("税前收入", format="¥%,.0f"),
                "五险一金": st.column_config.NumberColumn("五险一金", format="¥%,.0f"),
                "个人所得税": st.column_config.NumberColumn("个人所得税", format="¥%,.0f"),
                "税后收入": st.column_config.NumberColumn("税后收入", format="¥%,.0f"),
                "理财收入": st.column_config.NumberColumn("理财收入", format="¥%,.0f"),
            },
        )

        # ── 累计汇总 ──
        sum_pre = df["pre_tax_income"].sum()
        sum_post = df["post_tax_income"].sum()
        sum_social = df["social_insurance"].sum()
        sum_tax = df["income_tax"].sum()
        sum_invest = df["investment_income"].sum()
        n_years = len(df)

        footer_html = (
            '<hr style="border:none;border-top:2px solid #2D2D2D;margin:1.5rem 0 0.8rem 0">'
            '<div style="font-family:Georgia,serif;color:#2D2D2D;text-align:center">'
            '<div style="font-size:1.1rem;font-weight:700;margin-bottom:12px">'
            + str(n_years) + ' 年累计汇总</div>'
            '<div style="display:flex;justify-content:center;gap:32px;flex-wrap:wrap;font-size:0.95rem">'
            '<span>税前收入 <b>¥' + f"{sum_pre:,.0f}" + '</b></span>'
            '<span>税后收入 <b>¥' + f"{sum_post:,.0f}" + '</b></span>'
            '<span>五险一金 <b>¥' + f"{sum_social:,.0f}" + '</b></span>'
            '<span>个人所得税 <b>¥' + f"{sum_tax:,.0f}" + '</b></span>'
            '<span>理财收入 <b>¥' + f"{sum_invest:,.0f}" + '</b></span>'
            '</div></div>'
        )
        st.markdown(footer_html, unsafe_allow_html=True)

    else:
        st.caption("暂无年度数据，请先添加。")

    # ══════════════════════════════════════════════════════
    #  添加 / 更新年度数据
    # ══════════════════════════════════════════════════════

    st.markdown('<hr style="border:none;border-top:1px solid #C8C3B5;margin:1.5rem 0 0.5rem 0">',
                unsafe_allow_html=True)

    with st.expander("新增 / 更新年度数据", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        year = c1.number_input("年份", 2020, 2030, datetime.now().year)
        pre_tax = c2.number_input("税前收入", value=0.0, step=1000.0)
        social = c3.number_input("五险一金", value=0.0, step=1000.0)
        tax = c4.number_input("个人所得税", value=0.0, step=1000.0)

        c5, c6 = st.columns(2)
        invest = c5.number_input("理财收入", value=0.0, step=1000.0)
        note = c6.text_input("备注", placeholder="例如：预估年度")

        if st.button("保存年度数据", key="btn_yr_save", use_container_width=True):
            update_yearly_summary(year, pre_tax, social, tax, invest, note)
            st.rerun()
