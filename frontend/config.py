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
    "primary":    "#1a73e8",
    "secondary":  "#34a853",
    "danger":     "#ea4335",
    "warning":    "#fbbc04",
    "purple":     "#a142f4",
    "blue_light": "#4285f4",
    "bg_light":   "#f8f9fa",
    "border":     "#e0e7ff",
}

GLOBAL_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9f0ff 100%);
    }
    h1 { color: #1a73e8 !important; font-weight: 800; letter-spacing: -0.5px; }
    h2, h3 { color: #1a73e8 !important; font-weight: 700; }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1.5px solid #e0e7ff;
        box-shadow: 0 2px 10px rgba(26,115,232,0.06);
        transition: box-shadow .2s;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 6px 20px rgba(26,115,232,0.12);
    }

    .stButton > button {
        background: linear-gradient(135deg, #1a73e8, #1565c0);
        color: #fff !important;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        box-shadow: 0 3px 10px rgba(26,115,232,0.25);
        transition: all .2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1565c0, #0d47a1);
        box-shadow: 0 5px 14px rgba(26,115,232,0.35);
        transform: translateY(-1px);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f0f5ff 100%);
        border-right: 2px solid #e0e7ff;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #1a73e8 !important;
    }

    .stSelectbox, .stNumberInput, .stTextInput, .stDateInput {
        background-color: #ffffff !important;
    }

    details[data-testid="stExpander"] {
        border: 1.5px solid #e0e7ff;
        border-radius: 12px;
        background: #fff;
    }

    .stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
"""

# ═══════════════════════════════════════════════════════
#  股票中文名映射
# ═══════════════════════════════════════════════════════

STOCK_NAMES = {
    "AAPL":  "苹果",
    "MSFT":  "微软",
    "GOOGL": "谷歌",
    "AMZN":  "亚马逊",
    "TSLA":  "特斯拉",
    "NVDA":  "英伟达",
    "META":  "Meta",
    "VOO":   "标普500ETF",
    "QQQ":   "纳指100ETF",
    "SPY":   "标普500ETF",
    "IWM":   "罗素2000ETF",
    "GLD":   "黄金ETF",
    "SLV":   "白银ETF",
    "PLTR":  "Palantir",
    "AMD":   "超威半导体",
    "BABA":  "阿里巴巴",
    "JD":    "京东",
    "PDD":   "拼多多",
    "NIO":   "蔚来",
    "COIN":  "Coinbase",
    "SOFI":  "SoFi",
    "MARA":  "Marathon",
    "RIOT":  "Riot",
    "INTC":  "英特尔",
    "JPM":   "摩根大通",
    "BAC":   "美国银行",
    "DIS":   "迪士尼",
    "NFLX":  "奈飞",
    "V":     "Visa",
    "MA":    "万事达",
}

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
