"""
工具函数 - 汇率获取、金额转换、Plotly 布局、Metric 渲染、Transaction 转换
"""
import streamlit as st
from typing import Dict, List

from src.models import Transaction, TransactionType
from api.exchange_rates import get_exchange_rates as _api_get_rates
from api.stock_names import get_stock_label as _api_stock_label


# ═══════════════════════════════════════════════════════
#  汇率
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_exchange_rates() -> Dict:
    """获取汇率（缓存 1 小时）。 兼容旧接口 key 'rmb'"""
    raw = _api_get_rates()
    # api 返回 cny 键，前端历史代码用 rmb 键，做一层兼容
    return {
        "USD": {"usd": 1.0, "rmb": raw["USD"]["cny"]},
        "CNY": {"usd": raw["CNY"]["usd"], "rmb": 1.0},
        "HKD": {"usd": raw["HKD"]["usd"], "rmb": raw["HKD"]["cny"]},
    }


def to_rmb(amount: float, currency: str, rates: Dict) -> float:
    """金额 → 人民币"""
    if currency == "CNY":
        return amount
    return amount * rates.get(currency, {}).get("rmb", 1.0)


# ═══════════════════════════════════════════════════════
#  标签
# ═══════════════════════════════════════════════════════

def stock_label(symbol: str) -> str:
    """返回 'AAPL 苹果' 格式的标签（自动从 api/stock_names 获取）"""
    return _api_stock_label(symbol)


# ═══════════════════════════════════════════════════════
#  Plotly / Streamlit 工具
# ═══════════════════════════════════════════════════════

def plotly_layout(**overrides) -> dict:
    """统一 Plotly 布局参数 — 复古金融报告风格"""
    base = dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=40, b=40),
        font=dict(family="'Times New Roman', Georgia, serif", size=15,
                  color="#2D2D2D"),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor="#2D2D2D",
            linewidth=1,
            tickfont=dict(size=14, color="#2D2D2D",
                          family="'Times New Roman', Georgia, serif"),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor="#2D2D2D",
            linewidth=1,
            tickfont=dict(size=14, color="#2D2D2D",
                          family="'Times New Roman', Georgia, serif"),
        ),
        hoverlabel=dict(
            bgcolor="#FFFEF9",
            bordercolor="#2D2D2D",
            font=dict(family="'Times New Roman', Georgia, serif",
                      size=14, color="#2D2D2D"),
        ),
        legend=dict(
            font=dict(size=13, color="#2D2D2D",
                      family="'Times New Roman', Georgia, serif"),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    base.update(overrides)
    return base


def metric_row(cols_data: List[tuple]):
    """快速渲染一行 metric 卡片: [(label, value, delta?), ...]"""
    cols = st.columns(len(cols_data))
    for col, item in zip(cols, cols_data):
        label, value = item[0], item[1]
        delta = item[2] if len(item) > 2 else None
        col.metric(label, value, delta=delta)


# ═══════════════════════════════════════════════════════
#  Transaction 转换
# ═══════════════════════════════════════════════════════

def dict_to_transaction(d: Dict) -> Transaction:
    """数据库行（dict）→ Transaction 对象

    金额计算规则：
    - 期权: amount = ±(price × quantity × 100)  ← 1 张 = 100 股
    - 股票: amount = ±(price × quantity)
    - 手续费按张/笔计，不 ×100
    - 正数 = 支出，负数 = 收入
    """
    action = d.get("action", "")

    TYPE_MAP = {
        "BUY":        (TransactionType.STOCK,   "buy"),
        "SELL":       (TransactionType.STOCK,   "sell"),
        "STO":        (TransactionType.OPTION,  "sell_put"),
        "STO_CALL":   (TransactionType.OPTION,  "sell_call"),
        "STC":        (TransactionType.OPTION,  "buy_put"),
        "BTC":        (TransactionType.OPTION,  "buy_put"),
        "BTO_CALL":   (TransactionType.OPTION,  "buy_call"),
        "ASSIGNMENT": (TransactionType.STOCK,   "assignment"),
        "CALLED_AWAY":(TransactionType.STOCK,   "called_away"),
        "EXPENSE":    (TransactionType.EXPENSE, d.get("subcategory", "other")),
        "INCOME":     (TransactionType.INCOME,  d.get("subcategory", "other")),
    }
    tx_type, subtype = TYPE_MAP.get(action, (TransactionType.STOCK, None))

    qty = d.get("quantity", 1)
    price = d.get("price", 0)

    # ── 计算 amount（实际美元金额）──
    if tx_type == TransactionType.OPTION:
        multiplier = 100
        sign = -1 if subtype in ("sell_put", "sell_call") else 1
        amount = sign * price * qty * multiplier
    elif tx_type == TransactionType.STOCK:
        if subtype in ("sell", "called_away"):
            amount = -(price * qty)
        else:
            amount = price * qty
    else:
        amount = price * qty

    return Transaction(
        type=tx_type,
        subtype=subtype,
        date=d.get("datetime", "")[:10],
        amount=amount,
        symbol=d.get("symbol"),
        quantity=d.get("quantity"),
        price=d.get("price"),
        fees=d.get("fees", 0),
        category_id=d.get("category_id"),
        note=d.get("note"),
        strike_price=d.get("strike_price"),
        expiration_date=d.get("expiration_date"),
    )
