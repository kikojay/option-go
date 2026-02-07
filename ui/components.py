"""
UI 原子组件库 — 纯渲染，无业务逻辑

所有方法只做 HTML/Streamlit 渲染，不做任何业务计算。
依赖方向：ui/ → config/（主题）+ streamlit

设计原则：
- 用户文本经 html.escape() 防御处理
- 含移动端响应式规则（从 config/theme.py 导入）
- 不引用 services/ / pages/ / frontend/
"""
from __future__ import annotations

import html as _html
import re
from contextlib import contextmanager
from typing import Any, Optional, Sequence, Tuple, Union

import pandas as pd
import streamlit as st

try:
    from streamlit_extras.metric_cards import style_metric_cards
    from streamlit_extras.stylable_container import stylable_container
except Exception:  # pragma: no cover - 运行环境可能未装 extras
    style_metric_cards = None
    stylable_container = None

from config.theme import COLORS, GLOBAL_CSS, MOBILE_CSS, METRIC_CARD_STYLE


def _esc(text: Any) -> str:
    """防御性 HTML 转义"""
    return _html.escape(str(text)) if text is not None else ""


def _strip_html(text: Any) -> str:
    """去除标题中的 HTML 标签，仅保留纯文本"""
    return re.sub(r"<[^>]+>", "", str(text)) if text is not None else ""


class UI:
    """
    原子级 UI 组件库

    使用示例::
        from ui import UI
        UI.inject_css()
        UI.header("资产总览")
        UI.metric_row([("总资产", "¥1,234,567"), ("变化", "+3.2%")])
    """

    # ── 全局样式注入 ──

    @staticmethod
    def inject_css():
        """注入全局 CSS + 移动端响应式（每页调用一次）"""
        if GLOBAL_CSS:
            st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
        if MOBILE_CSS:
            st.markdown(MOBILE_CSS, unsafe_allow_html=True)
        if style_metric_cards:
            style_metric_cards(**METRIC_CARD_STYLE)

    # ── 卡片 ──

    @staticmethod
    def card(
        label: str,
        value: Union[float, str],
        *,
        delta: Optional[float] = None,
        subtext: str = "",
        currency: str = "¥",
        compact: bool = False,
    ):
        """
        金融风格指标卡片

        Args:
            label:    标题
            value:    数值（float 自动格式化，str 原样显示）
            delta:    变化率%（正绿负红）
            subtext:  附注
            currency: 货币符号
            compact:  True 则缩小字号
        """
        if isinstance(value, (int, float)):
            val_str = f"{value:,.2f}" if abs(value) < 10000 else f"{value:,.0f}"
            val_display = f"{currency} {val_str}"
        else:
            val_display = str(value)

        delta_display = None
        if delta is not None:
            sign = "+" if delta >= 0 else ""
            delta_display = f"{sign}{delta:.2f}%"

        st.metric(label=label, value=val_display, delta=delta_display)
        if subtext:
            st.caption(subtext)

        if style_metric_cards:
            style_metric_cards(**METRIC_CARD_STYLE)

    # ── 指标行 ──

    @staticmethod
    def metric_row(items: Sequence[Tuple[str, str, ...]]):
        """水平排列的指标行: [(label, value), ...] 或 [(label, value, delta), ...]"""
        cols = st.columns(len(items))
        for col, item in zip(cols, items):
            label = item[0]
            value = item[1]
            delta = item[2] if len(item) > 2 else None
            col.metric(label=label, value=value, delta=delta)

        if style_metric_cards:
            style_metric_cards(**METRIC_CARD_STYLE)

    # ── 标题 ──

    @staticmethod
    def header(title: str, subtitle: str = ""):
        """章节大标题（带 3px 底线）"""
        st.subheader(title)
        if subtitle:
            st.caption(subtitle)

    @staticmethod
    def sub_heading(title: str):
        """次级标题（带 1px 底线）"""
        st.markdown(f"### {title}")

    # ── Expander ──

    @staticmethod
    @contextmanager
    def expander(title: str, *, expanded: bool = False, key: Optional[str] = None):
        """带复古边框的折叠面板（使用容器包裹，避免污染内部结构）"""
        clean_title = _strip_html(title)
        if stylable_container:
            safe_key = key or f"expander_{abs(hash(clean_title))}"
            with stylable_container(
                key=safe_key,
                css_styles=(
                    "{"
                    "border: 2px solid #2D2D2D;"
                    "box-shadow: 4px 4px 0 #2D2D2D;"
                    "background: #F9F7F0;"
                    "padding: 6px 8px;"
                    "}"
                ),
            ):
                with st.expander(clean_title, expanded=expanded):
                    yield
        else:
            with st.expander(clean_title, expanded=expanded):
                yield

    # ── 列表项 ──

    @staticmethod
    def list_item(
        name: str,
        value_usd: Optional[float] = None,
        value_rmb: Optional[float] = None,
    ):
        """资产列表行（支持双币显示）"""
        n = _esc(name)
        val_html = ""
        if value_usd is not None and value_rmb is not None:
            val_html = (
                f'<div style="text-align:right">'
                f'<div class="numeric" style="font-size:16px;'
                f'color:{COLORS["text"]}">${value_usd:,.2f}</div>'
                f'<div class="numeric" style="font-size:13px;'
                f'color:{COLORS["text_muted"]}">¥{value_rmb:,.2f}</div></div>'
            )
        elif value_rmb is not None:
            val_html = (
                f'<div class="numeric" style="font-size:16px;'
                f'color:{COLORS["text"]}">¥{value_rmb:,.2f}</div>'
            )
        st.markdown(
            f'<div class="asset-item">'
            f'<span style="font-size:15px;font-weight:500">{n}</span>'
            f'{val_html}</div>',
            unsafe_allow_html=True,
        )

    # ── 分隔线 ──

    @staticmethod
    def divider(thick: bool = False):
        st.divider()

    # ── 底部汇总行 ──

    @staticmethod
    def footer(items: Sequence[Tuple[str, str]]):
        """水平排列的底部汇总: [(label, value), ...]"""
        spans = " ".join(
            f'<span>{_esc(lbl)} <b style="font-family:\'Times New Roman\',serif">'
            f'{_esc(val)}</b></span>'
            for lbl, val in items
        )
        st.markdown(
            f'<div style="font-family:Georgia,serif;font-size:0.9rem;color:{COLORS["text"]};'
            f'display:flex;gap:28px;flex-wrap:wrap;margin-top:6px">{spans}</div>',
            unsafe_allow_html=True,
        )

    # ── 数据表 ──

    @staticmethod
    def table(df: pd.DataFrame, title: str = "", max_height: int = 400):
        """数据表格（带边框）"""
        if title:
            st.markdown(
                f'<div style="font-weight:600;font-size:16px;margin-bottom:10px;'
                f'color:{COLORS["text"]}">{_esc(title)}</div>',
                unsafe_allow_html=True,
            )
        if stylable_container:
            key = f"table_{id(df)}"
            with stylable_container(
                key=key,
                css_styles=(
                    "{"
                    "border: 2px solid #2D2D2D;"
                    "box-shadow: 4px 4px 0 #2D2D2D;"
                    "background: #F9F7F0;"
                    "}"
                ),
            ):
                st.dataframe(
                    df, use_container_width=True, hide_index=True,
                    height=min(len(df) * 35 + 38, max_height),
                )
        else:
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                height=min(len(df) * 35 + 38, max_height),
            )

    # ── 进度条 ──

    @staticmethod
    def progress_bar(value: float, max_val: float = 1.0, label: str = ""):
        """轻量进度条（0-100%）"""
        pct = min(value / max_val * 100, 100) if max_val > 0 else 0
        lbl = _esc(label)
        bar_color = COLORS["gain"] if pct < 80 else COLORS["accent"]
        st.markdown(
            f'<div style="margin:6px 0">'
            f'<div style="display:flex;justify-content:space-between;font-size:13px;'
            f'color:{COLORS["text_muted"]};margin-bottom:4px">'
            f'<span>{lbl}</span><span>{pct:.1f}%</span></div>'
            f'<div style="background:#E8E5DC;height:8px;border-radius:0;overflow:hidden">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{bar_color}"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── 空状态 ──

    @staticmethod
    def empty(message: str = "暂无数据"):
        st.info(message)

    # ── 盈亏色 ──

    @staticmethod
    def pnl_color(value: float) -> str:
        """正值返回绿色，负值返回红色"""
        return COLORS["gain"] if value >= 0 else COLORS["loss"]

    @staticmethod
    def pnl_text(value: float, fmt: str = "{:+,.2f}") -> str:
        """带色彩的 HTML 数字文本"""
        c = COLORS["gain"] if value >= 0 else COLORS["loss"]
        return f'<span style="color:{c};font-weight:700">{fmt.format(value)}</span>'
