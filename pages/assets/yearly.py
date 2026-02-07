"""年度汇总页面 — 税前 · 税后 · 社保 · 投资收益"""
import streamlit as st
import plotly.graph_objects as go

from ui import UI, plotly_layout
from services import YearlyService
import db


def render():
    UI.inject_css()
    UI.header("年度汇总", "税前 · 税后 · 社保 · 投资收益")

    df = YearlyService.get_data()
    if df is None or df.empty:
        UI.empty("暂无年度数据")
        _add_form()
        return

    # 1. 汇总指标
    t = YearlyService.totals(df)
    UI.metric_row([
        ("税前合计", f"¥{t['pre_tax'] / 10000:,.1f}万"),
        ("税后合计", f"¥{t['post_tax'] / 10000:,.1f}万"),
        ("社保+个税", f"¥{(t['social'] + t['tax']) / 10000:,.1f}万"),
        ("投资收益", f"¥{t['invest'] / 10000:,.1f}万"),
    ])

    # 2. 收入对比图
    UI.sub_heading("收入对比")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["年份"], y=df["pre_tax_income"] / 10000,
                         name="税前", marker_color="#2B4C7E", width=0.3))
    fig.add_trace(go.Bar(x=df["年份"], y=df["post_tax_income"] / 10000,
                         name="税后", marker_color="#5B8C5A", width=0.3))
    fig.add_trace(go.Scatter(
        x=df["年份"], y=df["investment_income"] / 10000,
        name="投资", mode="lines+markers",
        line=dict(color="#D4A017", width=2.5)))
    fig.update_layout(**plotly_layout(height=350, hovermode="x unified"))
    fig.update_yaxes(title="万元")
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})

    # 3. 扣缴明细
    UI.sub_heading("扣缴明细")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df["年份"], y=df["social_insurance"] / 10000,
                          name="社保", marker_color="#6C3483", width=0.3))
    fig2.add_trace(go.Bar(x=df["年份"], y=df["income_tax"] / 10000,
                          name="个税", marker_color="#C0392B", width=0.3))
    fig2.update_layout(**plotly_layout(height=300, hovermode="x unified"))
    fig2.update_yaxes(title="万元")
    st.plotly_chart(fig2, use_container_width=True,
                    config={"displayModeBar": False})

    # 4. 数据表
    cols = ["年份", "pre_tax_income", "post_tax_income",
            "social_insurance", "income_tax", "investment_income", "note"]
    display = df[cols].copy()
    display.columns = ["年份", "税前收入", "税后收入",
                        "社保", "个税", "投资收益", "备注"]
    UI.table(display)

    # 5. 累计行
    UI.footer([
        ("税前合计", f"¥{t['pre_tax']:,.0f}"),
        ("税后合计", f"¥{t['post_tax']:,.0f}"),
        ("社保合计", f"¥{t['social']:,.0f}"),
        ("个税合计", f"¥{t['tax']:,.0f}"),
        ("投资合计", f"¥{t['invest']:,.0f}"),
    ])

    _add_form()


def _add_form():
    """年度数据录入。"""
    with UI.expander("添加/更新年度数据", expanded=False):
        c1, c2 = st.columns(2)
        year = c1.number_input("年份", min_value=2000, max_value=2099,
                               value=2024, step=1, key="yl_year")
        note = c2.text_input("备注", key="yl_note")
        c3, c4, c5, c6 = st.columns(4)
        pre_tax = c3.number_input("税前收入", value=0, step=1000, key="yl_pre")
        social = c4.number_input("社保", value=0, step=100, key="yl_soc")
        tax = c5.number_input("个税", value=0, step=100, key="yl_tax")
        invest = c6.number_input("投资收益", value=0, step=100, key="yl_inv")

        if st.button("保存", key="btn_add_yearly", use_container_width=True):
            db.yearly.upsert(
                int(year), pre_tax_income=pre_tax,
                social_insurance=social,
                income_tax=tax, investment_income=invest,
                note=note)
            st.rerun()
