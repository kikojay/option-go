"""
财富追踪器 v2.0
精简入口 —— 所有页面模块在 pages/ 目录
"""
import streamlit as st
from db.connection import init_database

from config import PAGE_CONFIG, GLOBAL_CSS
from config.theme import NAV_CSS
from utils.currency import fetch_exchange_rates
from pages import (
    page_overview, page_snapshots, page_yearly,
    page_expense, page_portfolio, page_trading,
    page_wheel, page_settings,
)

try:
    from streamlit_extras.stylable_container import stylable_container
except Exception:  # pragma: no cover - 运行环境可能未装 extras
    stylable_container = None


# ── 页面注册表 ──
PAGES = [
    # (label,        icon,                           handler)
    ("总览",      ":material/dashboard:",          page_overview),
    ("月度快照",  ":material/calendar_month:",     page_snapshots),
    ("年度汇总",  ":material/bar_chart:",          page_yearly),
    ("收支管理",  ":material/account_balance:",    page_expense),
    ("投资组合",  ":material/trending_up:",        page_portfolio),
    ("交易日志",  ":material/receipt_long:",       page_trading),
    ("期权车轮",  ":material/target:",             page_wheel),
    ("设置",     ":material/settings:",           page_settings),
]

PAGE_GROUPS = [
    ("资产追踪", ["月度快照", "年度汇总"]),
    ("日常记账", ["收支管理"]),
    ("投资监控", ["投资组合", "交易日志", "期权车轮"]),
]


def main():
    st.set_page_config(**PAGE_CONFIG)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(NAV_CSS, unsafe_allow_html=True)
    init_database()

    # ── 汇率写入 session_state（所有页面共享）──
    rates = fetch_exchange_rates()
    st.session_state.usd_rmb = rates["USD"]["rmb"]
    st.session_state.hkd_rmb = rates["HKD"]["rmb"]

    # ── 侧边栏 ──
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align:center;margin-bottom:0'>财富追踪器</h2>"
            "<p style='text-align:center;color:#7a8599;font-size:13px;margin-top:2px'>Wealth Tracker v2.0</p>",
            unsafe_allow_html=True,
        )
        st.markdown("")  # spacer

        page_map = {label: (icon, handler) for label, icon, handler in PAGES}

        def _nav_label(label: str | None) -> str:
            if not label:
                return ""
            icon, _handler = page_map.get(label, ("", None))
            return f"{icon} {label}"

        def _render_group(title: str, labels: list[str], key: str, current: str) -> str:
            st.caption(title)
            options = [None] + labels
            index = options.index(current) if current in labels else 0
            picked = st.radio(
                label=title,
                options=options,
                index=index,
                format_func=_nav_label,
                key=key,
                label_visibility="collapsed",
            )
            if picked:
                st.session_state.nav_selected = picked
                return picked
            return current

        current = st.session_state.get("nav_selected", "总览")
        if stylable_container:
            with stylable_container(
                key="sidebar_nav",
                css_styles=(
                    "{"
                    "padding: 0;"
                    "}"
                    "span[class*='material'] {"
                    "color: #D4AF37 !important;"
                    "font-size: 1.5rem !important;"
                    "}"
                    "div[role='radiogroup'] label[data-checked='true'] {"
                    "background-color: #333333 !important;"
                    "border-left: 4px solid #228B22 !important;"
                    "}"
                ),
            ):
                current = _render_group("总览", ["总览"], "nav_overview", current)
                for group_title, labels in PAGE_GROUPS:
                    current = _render_group(group_title, labels, f"nav_{group_title}", current)
                current = _render_group("设置", ["设置"], "nav_settings", current)
        else:
            current = _render_group("总览", ["总览"], "nav_overview", current)
            for group_title, labels in PAGE_GROUPS:
                current = _render_group(group_title, labels, f"nav_{group_title}", current)
            current = _render_group("设置", ["设置"], "nav_settings", current)

        st.markdown("---")
        st.caption("© 2026 · [GitHub](https://github.com/kikojay/option-go)")

    # ── 路由 ──
    handler = page_map.get(current, (None, page_overview))[1]
    handler()


if __name__ == "__main__":
    main()
