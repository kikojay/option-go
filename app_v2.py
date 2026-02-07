"""
💰 财富追踪器 v2.0
精简入口 —— 所有页面模块在 frontend/ 目录
"""
import streamlit as st
from src.database_v2 import init_database

from frontend.config import PAGE_CONFIG, GLOBAL_CSS
from frontend.page_overview import page_overview
from frontend.page_snapshots import page_snapshots
from frontend.page_yearly import page_yearly_summary
from frontend.page_expense import page_expense_tracker
from frontend.page_portfolio import page_portfolio
from frontend.page_trading_log import page_trading_log
from frontend.page_wheel import page_wheel
from frontend.page_settings import page_settings


# ── 页面注册表 ──
PAGES = [
    # (label,        icon,                           handler)
    ("📊 总览",      ":material/dashboard:",          page_overview),
    ("📅 月度快照",  ":material/calendar_month:",     page_snapshots),
    ("📆 年度汇总",  ":material/bar_chart:",          page_yearly_summary),
    ("💸 收支管理",  ":material/account_balance:",    page_expense_tracker),
    ("📈 投资组合",  ":material/trending_up:",        page_portfolio),
    ("📝 交易日志",  ":material/receipt_long:",       page_trading_log),
    ("🎯 期权车轮",  ":material/target:",             page_wheel),
    ("⚙️ 设置",     ":material/settings:",           page_settings),
]

# ── 侧边栏导航 CSS ──
_NAV_CSS = """
<style>
    /* 侧边栏 radio 导航 — 复古风格 */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 2px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        padding: 12px 18px !important;
        border-radius: 0 !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        color: #2D2D2D !important;
        cursor: pointer;
        transition: all 0.15s;
        background: transparent !important;
        border: none !important;
        border-left: 3px solid transparent !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #EDE9DD !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #2B4C7E !important;
        color: #F9F7F0 !important;
        font-weight: 700 !important;
        border-left: 3px solid #D4A017 !important;
        box-shadow: none !important;
    }
    /* 隐藏 radio 圆点 */
    section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-size: 15px !important;
    }
</style>
"""


def main():
    st.set_page_config(**PAGE_CONFIG)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(_NAV_CSS, unsafe_allow_html=True)
    init_database()

    # ── 侧边栏 ──
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align:center;margin-bottom:0'>💰 财富追踪器</h2>"
            "<p style='text-align:center;color:#7a8599;font-size:13px;margin-top:2px'>Wealth Tracker v2.0</p>",
            unsafe_allow_html=True,
        )
        st.markdown("")  # spacer

        page_labels = [p[0] for p in PAGES]
        selected = st.radio(
            label="导航",
            options=page_labels,
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.caption("© 2026 · [GitHub](https://github.com/kikojay/option-go)")

    # ── 路由 ──
    page_map = {p[0]: p[2] for p in PAGES}
    handler = page_map.get(selected, page_overview)
    handler()


if __name__ == "__main__":
    main()
