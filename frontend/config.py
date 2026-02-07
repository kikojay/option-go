"""
全局配置 & 常量
把颜色、CSS、股票名映射、操作翻译等集中管理
"""

# ═══════════════════════════════════════════════════════
#  Streamlit 页面配置
# ═══════════════════════════════════════════════════════

PAGE_CONFIG = dict(
    page_title="💰 财富追踪器",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
#  颜色 & CSS
# ═══════════════════════════════════════════════════════

COLORS = {
    "primary":    "#2B4C7E",
    "secondary":  "#5B8C5A",
    "danger":     "#C0392B",
    "warning":    "#D4A017",
    "purple":     "#6C3483",
    "blue_light": "#3B7DD8",
    "bg_light":   "#F9F7F0",
    "border":     "#C8C3B5",
    "gain":       "#5B8C5A",
    "loss":       "#C0392B",
    "text":       "#2D2D2D",
    "text_muted": "#6B6B6B",
}

GLOBAL_CSS = """
<style>
    /* ── Hide Material Symbols fallback text (sidebar collapse btn) ── */
    button[kind="header"] span.material-symbols-rounded,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] span {
        font-size: 0 !important;
        overflow: hidden !important;
    }
    button[kind="header"] span.material-symbols-rounded::after,
    [data-testid="stSidebarCollapseButton"] span::after,
    [data-testid="collapsedControl"] span::after {
        content: "\276E";
        font-size: 16px;
        font-family: serif;
    }
    [data-testid="collapsedControl"] span::after {
        content: "\276F";
    }

    /* ── Global — vintage parchment ── */
    .stApp {
        font-family: Georgia, 'Times New Roman', serif !important;
        background: #F9F7F0 !important;
        color: #2D2D2D;
    }
    html, body, [class*="st-"] {
        font-family: Georgia, 'Times New Roman', serif !important;
    }

    /* ── Headings — serif, black ── */
    h1 {
        color: #2D2D2D !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: 0;
        border-bottom: 3px solid #2D2D2D;
        padding-bottom: 8px;
    }
    h2 {
        color: #2D2D2D !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
    }
    h3 {
        color: #3D3D3D !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* ── Metric cards — flat, no bg, fine line separators ── */
    div[data-testid="stMetric"] {
        background: transparent !important;
        border-radius: 0 !important;
        padding: 10px 12px;
        border: none !important;
        box-shadow: none !important;
        border-right: 1px solid #C8C3B5 !important;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: none !important;
        transform: none !important;
    }
    div[data-testid="stMetric"] label {
        color: #6B6B6B !important;
        font-size: 12px !important;
        font-weight: 400 !important;
        font-family: Georgia, serif !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #2D2D2D !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        font-family: 'Times New Roman', Georgia, serif !important;
    }
    div[data-testid="stMetricDelta"] svg { width: 14px; height: 14px; }

    /* ── Sidebar — parchment, spacious ── */
    section[data-testid="stSidebar"] {
        background: #F4F1E8 !important;
        border-right: 2px solid #2D2D2D !important;
        border-radius: 0 !important;
        padding-top: 1rem !important;
    }
    section[data-testid="stSidebar"] .stMarkdown hr {
        border-color: #C8C3B5;
    }
    section[data-testid="stSidebar"] a {
        color: #8A8A8A !important;
        text-decoration: none !important;
    }
    section[data-testid="stSidebar"] a:hover {
        color: #2D2D2D !important;
    }

    /* ── Buttons — vintage flat ── */
    .stButton > button {
        background: #2B4C7E !important;
        color: #F9F7F0 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 0 !important;
        font-weight: 600;
        font-size: 13px;
        font-family: Georgia, serif !important;
        padding: 0.45rem 1rem;
        box-shadow: none !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover {
        background: #1E3A5F !important;
        box-shadow: none !important;
    }

    /* ── Form inputs — flat ── */
    .stSelectbox, .stNumberInput, .stTextInput, .stDateInput {
        background-color: #FFFEF9 !important;
    }
    .stSelectbox > div, .stNumberInput > div, .stTextInput > div, .stDateInput > div {
        border-radius: 0 !important;
    }

    /* ── Expander — solid border, no radius ── */
    details[data-testid="stExpander"] {
        border: 1px solid #2D2D2D !important;
        border-radius: 0 !important;
        background: #FFFEF9 !important;
    }

    /* ── DataFrames — solid border, no shadow ── */
    .stDataFrame {
        border-radius: 0 !important;
        overflow: hidden;
        border: 1px solid #2D2D2D !important;
        box-shadow: none !important;
    }
    .stDataFrame [data-testid="glideDataEditor"] {
        border-radius: 0 !important;
    }

    /* ── Tabs — serif ── */
    button[data-baseweb="tab"] {
        font-family: Georgia, serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border-radius: 0 !important;
    }

    /* ── Section Divider — thick black line ── */
    .section-divider {
        border: none;
        border-top: 2px solid #2D2D2D;
        margin: 1.5rem 0;
    }
    /* thin variant */
    .section-divider-thin {
        border: none;
        border-top: 1px solid #2D2D2D;
        margin: 1.2rem 0;
    }

    /* ── Plotly chart container — hard edges ── */
    .stPlotlyChart {
        border-radius: 0 !important;
        overflow: hidden;
    }

    /* ── Remove all remaining rounded corners ── */
    [data-testid="stContainer"],
    [data-testid="stForm"],
    .stAlert {
        border-radius: 0 !important;
    }
</style>
"""

# ═══════════════════════════════════════════════════════
#  操作中文翻译
# ═══════════════════════════════════════════════════════

ACTION_CN = {
    "BUY":         "买入",
    "SELL":        "卖出",
    "STO":         "卖出Put",
    "STO_CALL":    "卖出Call",
    "STC":         "买回Put",
    "BTC":         "买回平仓",
    "BTO_CALL":    "买入Call",
    "ASSIGNMENT":  "被行权接盘",
    "CALLED_AWAY": "被行权卖出",
    "DIVIDEND":    "分红",
    "INCOME":      "收入",
    "EXPENSE":     "支出",
}

ACTION_LABELS = {
    "STO":      "卖出 Put",
    "STO_CALL": "卖出 Call",
    "STC":      "买回 Put",
    "BTC":      "买回平仓",
    "BTO_CALL": "买入 Call",
}

TRADE_ACTIONS = [
    "BUY", "SELL",
    "STO (卖Put)", "STO_CALL (卖Call)",
    "BTC (买回平仓)", "BTO_CALL (买Call)",
    "ASSIGNMENT", "DIVIDEND",
]

EXPENSE_CATEGORIES = [
    "餐饮", "房租", "交通", "家庭", "外食", "日用",
    "在家吃饭", "订阅", "工资", "投资", "分红", "其他",
]

# ═══════════════════════════════════════════════════════
#  账户类别中文翻译
# ═══════════════════════════════════════════════════════

CATEGORY_CN = {
    "cash":            "现金",
    "stock":           "股票",
    "etf":             "ETF",
    "crypto":          "加密货币",
    "provident_fund":  "公积金",
    "receivable":      "应收账款",
    "other":           "其他",
}
