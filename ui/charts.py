"""
Plotly 图表工具 — 统一布局 + 渲染封装

所有 Plotly 图表使用此模块的 plotly_layout() 获取布局参数，
确保全系统复古金融报告风格统一。

依赖方向：ui/ → config/（主题）+ plotly + streamlit
"""
from __future__ import annotations

from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

from config.theme import COLORS, PLOTLY_LAYOUT_DEFAULTS


def plotly_layout(**overrides: Any) -> Dict[str, Any]:
    """
    构建统一 Plotly 布局参数

    用法::
        fig.update_layout(**plotly_layout(height=350, hovermode="x unified"))

    基于 config/theme.py 的 PLOTLY_LAYOUT_DEFAULTS，
    支持任意 override 覆盖。
    """
    layout = dict(PLOTLY_LAYOUT_DEFAULTS)
    layout.update(overrides)
    return layout


def render_chart(fig: go.Figure, **kwargs: Any) -> None:
    """
    渲染 Plotly 图表（统一配置）

    自动设置 use_container_width=True 和关闭工具栏。

    用法::
        render_chart(fig)
        render_chart(fig, key="my_chart")
    """
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        **kwargs,
    )


def color_for_value(value: float) -> str:
    """根据数值正负返回盈亏颜色"""
    return COLORS["gain"] if value >= 0 else COLORS["loss"]
