"""子页面 2 — 持仓明细 (Holdings)"""
import streamlit as st
import pandas as pd

from ui import UI
from services import PortfolioService


def render(data: dict) -> None:
    """渲染持仓明细 Tab"""
    UI.sub_heading("持仓明细 · USD / RMB 双币对照")

    rows = PortfolioService.build_holdings_rows(data)
    if not rows:
        st.caption("暂无持仓")
        return

    usd_rmb = data["usd_rmb"]

    df = pd.DataFrame(rows)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        height=min(450, 38 * (len(rows) + 1)),
        column_config={
            "symbol": st.column_config.TextColumn("代号", width="small"),
            "company": st.column_config.TextColumn("公司", width="small"),
            "shares": st.column_config.NumberColumn("股数", format="%d"),
            "price_usd": st.column_config.NumberColumn("现价($)", format="$%.2f"),
            "change_pct": st.column_config.NumberColumn("涨跌%", format="%.2f%%"),
            "cost_usd": st.column_config.NumberColumn("成本($)", format="$%,.0f"),
            "cost_rmb": st.column_config.NumberColumn("成本(¥)", format="¥%,.0f"),
            "value_usd": st.column_config.NumberColumn("市值($)", format="$%,.0f"),
            "value_rmb": st.column_config.NumberColumn("市值(¥)", format="¥%,.0f"),
            "adjusted_cost_per_share": st.column_config.NumberColumn(
                "调整成本/股", format="$%.2f"
            ),
            "premiums": st.column_config.NumberColumn("权利金", format="$%,.0f"),
            "pnl_usd": st.column_config.NumberColumn("盈亏($)", format="$%,.0f"),
            "pnl_rmb": st.column_config.NumberColumn("盈亏(¥)", format="¥%,.0f"),
            "monthly_dividend_usd": st.column_config.NumberColumn(
                "预估月分红", format="$%.2f"
            ),
            "yearly_dividend_usd": st.column_config.NumberColumn(
                "预估年收息", format="$%.2f"
            ),
            "weight": st.column_config.ProgressColumn(
                "占比", format="%.0f%%", min_value=0, max_value=1
            ),
        })

    # 合计行
    footer = PortfolioService.calc_holdings_footer(rows, usd_rmb)
    if footer:
        UI.footer(footer)
