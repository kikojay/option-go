"""
主题配置 — 颜色、CSS、Plotly 布局

所有视觉风格的唯一定义处。UI 组件只引用此文件。
"""
from typing import Dict, Any

# ═══════════════════════════════════════════════════════
#  颜色定义
# ═══════════════════════════════════════════════════════

COLORS: Dict[str, str] = {
    # 品牌色
    "primary":     "#2D2D2D",
    "secondary":   "#228B22",
    "danger":      "#B22222",
    "warning":     "#2D2D2D",
    "purple":      "#2D2D2D",
    "blue_light":  "#2D2D2D",

    # 背景
    "bg_main":     "#F9F7F0",
    "bg_card":     "#F9F7F0",
    "bg_light":    "#F9F7F0",
    "bg_sidebar":  "#2D2D2D",
    "bg_input":    "#F9F7F0",

    # 边框
    "border":      "#2D2D2D",
    "border_light": "#C8C3B5",

    # 文字
    "text":        "#2D2D2D",
    "text_muted":  "#2D2D2D",
    "text_dark":   "#2D2D2D",

    # 盈亏色
    "gain":        "#228B22",
    "loss":        "#B22222",

    # 强调色
    "accent":      "#2D2D2D",
}


# ═══════════════════════════════════════════════════════
#  全局 CSS
# ═══════════════════════════════════════════════════════

GLOBAL_CSS: str = ""
# ═══════════════════════════════════════════════════════
#  移动端响应式 CSS
# ═══════════════════════════════════════════════════════

MOBILE_CSS: str = ""


# ═══════════════════════════════════════════════════════
#  侧边栏导航 CSS
# ═══════════════════════════════════════════════════════

NAV_CSS: str = ""


# ═══════════════════════════════════════════════════════
#  metric_cards 样式参数（streamlit-extras）
# ═══════════════════════════════════════════════════════

METRIC_CARD_STYLE: Dict[str, str] = {
    "background_color": "#F9F7F0",
    "border_color": "#2D2D2D",
    "border_left_color": "#2D2D2D",
    "box_shadow": "0 0 6px rgba(0, 0, 0, 0.2)",
}


# ═══════════════════════════════════════════════════════
#  Plotly 布局默认配置 — 复古金融报告风格
# ═══════════════════════════════════════════════════════

PLOTLY_LAYOUT_DEFAULTS: Dict[str, Any] = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=40, b=40),
    font=dict(
        family="'Times New Roman', Georgia, serif",
        size=15,
        color="#2D2D2D",
    ),
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        linecolor="#2D2D2D",
        linewidth=1,
        tickfont=dict(
            size=14, color="#2D2D2D",
            family="'Times New Roman', Georgia, serif",
        ),
    ),
    yaxis=dict(
        showgrid=False,
        zeroline=False,
        linecolor="#2D2D2D",
        linewidth=1,
        tickfont=dict(
            size=14, color="#2D2D2D",
            family="'Times New Roman', Georgia, serif",
        ),
    ),
    hoverlabel=dict(
        bgcolor="#FFFEF9",
        bordercolor="#2D2D2D",
        font=dict(
            family="'Times New Roman', Georgia, serif",
            size=14, color="#2D2D2D",
        ),
    ),
    legend=dict(
        font=dict(
            size=13, color="#2D2D2D",
            family="'Times New Roman', Georgia, serif",
        ),
        bgcolor="rgba(0,0,0,0)",
    ),
)
