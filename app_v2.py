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


# ── 页面注册表（模块 → 页面列表） ──
MODULES = {
    "🏠 个人资产管理": [
        ("📊 总览",      page_overview),
        ("📅 月度快照",  page_snapshots),
        ("📆 年度汇总",  page_yearly_summary),
        ("💸 支出/收入", page_expense_tracker),
    ],
    "📈 投资追踪": [
        ("📈 投资组合",  page_portfolio),
        ("📝 交易日志",  page_trading_log),
        ("🎯 期权车轮",  page_wheel),
    ],
    "⚙️ 系统": [
        ("⚙️ 设置", page_settings),
    ],
}


def main():
    st.set_page_config(**PAGE_CONFIG)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    init_database()

    # ── 侧边栏：列出全部模块和页面，一键切换 ──
    with st.sidebar:
        st.title("💰 财富追踪器")
        st.markdown("---")

        # 构建所有页面的 flat 列表（用于 radio）
        all_pages = []          # [(display_label, handler)]
        module_headers = {}     # display_label → module_name（用来插标题）

        for mod_name, pages in MODULES.items():
            for label, handler in pages:
                all_pages.append((label, handler))
                module_headers[label] = mod_name

        # 用 radio 展示，label 前带模块分组前缀
        page_labels = [label for label, _ in all_pages]

        # 自定义渲染：按模块分组显示
        if "current_page" not in st.session_state:
            st.session_state.current_page = page_labels[0]

        for mod_name, pages in MODULES.items():
            st.markdown(f"### {mod_name}")
            for label, handler in pages:
                if st.button(
                    label,
                    key=f"nav_{label}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_page == label else "secondary",
                ):
                    st.session_state.current_page = label

        st.markdown("---")
        st.caption("v2.0 · [GitHub](https://github.com/kikojay/option-go)")

    # ── 路由 ──
    page_map = {label: handler for label, handler in all_pages}
    handler = page_map.get(st.session_state.current_page, page_overview)
    handler()


if __name__ == "__main__":
    main()
