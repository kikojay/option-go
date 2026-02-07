"""投资组合主页面 — 布局和 Tab 切换"""
import streamlit as st

from ui import UI
from services import PortfolioService

from . import tab_overview, tab_holdings, tab_options


def render() -> None:
    """投资组合页面入口"""
    UI.inject_css()
    UI.header("投资组合", "Portfolio · 总览趋势 / 持仓明细 / 期权策略")

    usd_rmb = st.session_state.usd_rmb

    data = PortfolioService.load(usd_rmb)
    if data is None:
        st.info("暂无投资数据，去交易日志添加吧")
        return
    if not data["holdings"]:
        st.info("暂无持仓")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        st.caption(f"当前汇率: 1 USD = ¥{usd_rmb:.2f} CNY")
    with c2:
        if st.button("手动刷新行情", use_container_width=True):
            PortfolioService.get_live_prices.clear()
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["总览趋势", "持仓明细", "期权策略"])
    with tab1:
        tab_overview.render(data)
    with tab2:
        tab_holdings.render(data)
    with tab3:
        tab_options.render(data)
