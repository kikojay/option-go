#!/usr/bin/env python3
"""
Option Wheel Tracker v2.0 - 财富追踪器
重构版：模块化页面、统一样式、清晰路由
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# ── 路径准备 ──
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.database_v2 import (
    init_database, get_connection,
    add_transaction, get_transactions,
    get_all_accounts, create_snapshot, get_all_snapshots,
    get_yearly_summary, update_yearly_summary,
    get_strategies, get_portfolio_summary, convert_to_rmb, update_exchange_rate,
)
from src import (
    Transaction, TransactionType,
    PortfolioCalculator, PortfolioAnalyzer,
    WheelCalculator,
)


# ═══════════════════════════════════════════════════════
#  全局配置 & 样式
# ═══════════════════════════════════════════════════════

PAGE_CONFIG = dict(
    page_title="💰 财富追踪器",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 股票中文名映射
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

def _stock_label(symbol: str) -> str:
    """返回 'AAPL 苹果' 格式的标签"""
    cn = STOCK_NAMES.get(symbol, "")
    return f"{symbol} {cn}" if cn else symbol

# 操作中文翻译（全局共用）
ACTION_CN = {
    "BUY":        "买入",
    "SELL":       "卖出",
    "STO":        "卖出Put",
    "STO_CALL":   "卖出Call",
    "STC":        "买回Put",
    "BTC":        "买回平仓",
    "BTO_CALL":   "买入Call",
    "ASSIGNMENT": "被行权接盘",
    "CALLED_AWAY":"被行权卖出",
    "DIVIDEND":   "分红",
    "INCOME":     "收入",
    "EXPENSE":    "支出",
}

# 全局颜色常量
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
    /* ─── 背景 ─── */
    .stApp {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9f0ff 100%);
    }

    /* ─── 标题 ─── */
    h1 { color: #1a73e8 !important; font-weight: 800; letter-spacing: -0.5px; }
    h2, h3 { color: #1a73e8 !important; font-weight: 700; }

    /* ─── Metric 卡片 ─── */
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

    /* ─── 按钮 ─── */
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

    /* ─── 侧边栏 ─── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f0f5ff 100%);
        border-right: 2px solid #e0e7ff;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #1a73e8 !important;
    }

    /* ─── 表单组件 ─── */
    .stSelectbox, .stNumberInput, .stTextInput, .stDateInput {
        background-color: #ffffff !important;
    }

    /* ─── Expander ─── */
    details[data-testid="stExpander"] {
        border: 1.5px solid #e0e7ff;
        border-radius: 12px;
        background: #fff;
    }

    /* ─── DataFrame ─── */
    .stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
"""


# ═══════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_exchange_rates() -> Dict:
    """获取汇率（缓存 1 小时）"""
    defaults = {
        "USD": {"usd": 1.0, "rmb": 7.2},
        "CNY": {"usd": 0.14, "rmb": 1.0},
        "HKD": {"usd": 0.128, "rmb": 1.0},
    }
    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD", timeout=5
        )
        if resp.status_code == 200:
            cny_rate = resp.json()["rates"].get("CNY", 7.2)
            return {
                "USD": {"usd": 1.0, "rmb": cny_rate},
                "CNY": {"usd": 1 / cny_rate, "rmb": 1.0},
                "HKD": {"usd": 1 / 7.8, "rmb": 1 / 0.98},
            }
    except Exception:
        pass
    return defaults


def _to_rmb(amount: float, currency: str, rates: Dict) -> float:
    """金额 → 人民币"""
    if currency == "CNY":
        return amount
    return amount * rates.get(currency, {}).get("rmb", 1.0)


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
        # 1 张期权 = 100 股；卖出 → 收入(负)，买入 → 支出(正)
        multiplier = 100
        sign = -1 if subtype in ("sell_put", "sell_call") else 1
        amount = sign * price * qty * multiplier
    elif tx_type == TransactionType.STOCK:
        # 卖出/被行权卖出 → 收入(负)
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


def _plotly_layout(**overrides) -> dict:
    """统一 Plotly 布局参数"""
    base = dict(
        template="plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8f9fa",
        margin=dict(l=40, r=20, t=40, b=40),
        font=dict(family="Inter, sans-serif", size=13),
    )
    base.update(overrides)
    return base


def _metric_row(cols_data: List[tuple]):
    """快速渲染一行 metric 卡片: [(label, value, delta?), ...]"""
    cols = st.columns(len(cols_data))
    for col, item in zip(cols, cols_data):
        label, value = item[0], item[1]
        delta = item[2] if len(item) > 2 else None
        col.metric(label, value, delta=delta)


# ═══════════════════════════════════════════════════════
#  页面：总览
# ═══════════════════════════════════════════════════════

def page_overview():
    st.title("📊 总览 Overview")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    st.info(
        f"💱 实时汇率: 1 USD = ¥{usd_rmb:.2f} CNY · 1 HKD = ¥{rates['HKD']['rmb']:.2f} CNY"
    )

    accounts = get_all_accounts()

    # ── 总资产计算 ──
    total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
    total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
    total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
    total_rmb = total_usd * usd_rmb + total_cny + total_hkd * rates["HKD"]["rmb"]

    # ── 投资组合 ──
    tx_raw = get_transactions(category="投资", limit=500)
    transactions = [dict_to_transaction(t) for t in tx_raw]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💰 总资产")
        _metric_row([
            ("美元 (USD)", f"${total_usd:,.0f}"),
            ("折合人民币", f"¥{total_rmb:,.0f}"),
        ])

    with col_right:
        st.subheader("📈 投资组合")
        if transactions:
            calc = PortfolioCalculator(transactions)
            summary = calc.get_portfolio_summary()
            holdings = summary.get("holdings", {})
            market_val = sum(
                h.get("cost_basis", 0) for h in holdings.values()
            )
            _metric_row([
                ("市值 (USD)", f"${market_val:,.0f}"),
                ("浮动盈亏", f"${summary['total_unrealized_pnl']:,.0f}"),
            ])
        else:
            st.caption("暂无投资数据")

    # ── 图表行 ──
    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.subheader("🏦 资产配置")
        if accounts:
            cat_assets: Dict[str, float] = {}
            for a in accounts:
                cat_assets[a["category"]] = cat_assets.get(a["category"], 0) + _to_rmb(
                    a["balance"], a["currency"], rates
                )
            if cat_assets:
                fig = go.Figure(go.Pie(
                    labels=list(cat_assets.keys()),
                    values=list(cat_assets.values()),
                    hole=0.5,
                    marker=dict(colors=px.colors.qualitative.Set3),
                ))
                fig.update_layout(**_plotly_layout(height=340))
                st.plotly_chart(fig, use_container_width=True)

    with chart_right:
        st.subheader("📈 持仓概览")
        if transactions:
            symbols = list(holdings.keys())
            values = [h.get("cost_basis", 0) for h in holdings.values()]
            fig = go.Figure(go.Bar(
                x=symbols, y=values,
                marker_color=COLORS["primary"],
            ))
            fig.update_layout(**_plotly_layout(
                xaxis_title="标的", yaxis_title="成本 ($)", height=340
            ))
            st.plotly_chart(fig, use_container_width=True)

    # ── 账户明细 ──
    st.subheader("🏦 账户明细")
    if accounts:
        df = pd.DataFrame(accounts)
        df["余额_RMB"] = df.apply(
            lambda x: _to_rmb(x["balance"], x["currency"], rates), axis=1
        )
        display = df[["name", "category", "currency", "balance", "余额_RMB"]].copy()
        display.columns = ["账户", "类别", "币种", "原币余额", "折合(RMB)"]
        st.dataframe(display, use_container_width=True)


# ═══════════════════════════════════════════════════════
#  页面：月度快照
# ═══════════════════════════════════════════════════════

def page_snapshots():
    st.title("📅 月度快照 Snapshots")

    with st.expander("📝 创建新快照", expanded=False):
        accounts = get_all_accounts()
        rates = fetch_exchange_rates()

        if st.button("📸 从当前账户生成快照"):
            total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
            total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
            total_rmb = total_usd * rates["USD"]["rmb"] + total_cny

            create_snapshot(
                date_str=datetime.now().strftime("%Y-%m-%d"),
                total_assets_usd=total_usd,
                total_assets_rmb=total_rmb,
                assets_data={
                    "accounts": [
                        {"name": a["name"], "balance": a["balance"], "currency": a["currency"]}
                        for a in accounts
                    ]
                },
                note="自动生成",
            )
            st.success("✅ 快照已创建！")
            st.rerun()

    snapshots = get_all_snapshots()
    if not snapshots:
        st.caption("暂无快照")
        return

    df = pd.DataFrame(snapshots)

    fig = go.Figure(go.Scatter(
        x=df["date"], y=df["total_assets_rmb"],
        mode="lines+markers",
        name="总资产 (RMB)",
        line=dict(color=COLORS["primary"], width=2),
        fill="tozeroy",
        fillcolor="rgba(26,115,232,0.08)",
    ))
    fig.update_layout(**_plotly_layout(
        xaxis_title="日期", yaxis_title="资产 (RMB)", hovermode="x unified"
    ))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["date", "total_assets_usd", "total_assets_rmb", "note"]],
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════
#  页面：年度汇总
# ═══════════════════════════════════════════════════════

def page_yearly_summary():
    st.title("📆 年度汇总 Yearly Summary")

    with st.expander("➕ 添加/更新年度数据", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        year     = c1.number_input("年份", 2020, 2030, datetime.now().year)
        pre_tax  = c2.number_input("税前收入", value=0.0)
        social   = c3.number_input("五险一金", value=0.0)
        tax      = c4.number_input("个人所得税", value=0.0)

        c5, c6 = st.columns(2)
        invest = c5.number_input("理财收入", value=0.0)
        note   = c6.text_input("备注")

        if st.button("💾 保存"):
            update_yearly_summary(year, pre_tax, social, tax, invest, note)
            st.success("✅ 已保存！")
            st.rerun()

    summaries = get_yearly_summary()
    if not summaries:
        st.caption("暂无年度数据")
        return

    df = pd.DataFrame(summaries)

    left, right = st.columns(2)
    with left:
        st.subheader("📈 收入对比")
        fig = go.Figure([
            go.Bar(name="税前", x=df["year"], y=df["pre_tax_income"],
                   marker_color=COLORS["primary"]),
            go.Bar(name="税后", x=df["year"], y=df["post_tax_income"],
                   marker_color=COLORS["secondary"]),
        ])
        fig.update_layout(**_plotly_layout(barmode="group"))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📊 扣缴明细")
        fig = go.Figure([
            go.Bar(name="五险一金", x=df["year"], y=df["social_insurance"],
                   marker_color=COLORS["danger"]),
            go.Bar(name="个税", x=df["year"], y=df["income_tax"],
                   marker_color=COLORS["warning"]),
        ])
        fig.update_layout(**_plotly_layout())
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)


# ═══════════════════════════════════════════════════════
#  页面：支出/收入
# ═══════════════════════════════════════════════════════

EXPENSE_CATEGORIES = [
    "餐饮", "房租", "交通", "家庭", "外食", "日用",
    "在家吃饭", "订阅", "工资", "投资", "分红", "其他",
]

def page_expense_tracker():
    st.title("💸 支出与收入 Tracker")
    st.caption("记录每月收支，分析消费习惯")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ── 新增记录 ──
    with st.expander("➕ 记一笔", expanded=False):
        c1, c2, c3 = st.columns(3)
        tx_type  = c1.selectbox("类型", ["EXPENSE", "INCOME"])
        amount   = c2.number_input("金额", value=0.0)
        currency = c3.selectbox("币种", ["USD", "CNY", "HKD"])

        c4, c5, c6 = st.columns(3)
        category    = c4.selectbox("分类", EXPENSE_CATEGORIES)
        subcategory = c5.text_input("子分类（可选）")
        target      = c6.text_input("对象（可选）")

        c7, c8 = st.columns(2)
        note     = c7.text_input("备注")
        date_val = c8.date_input("日期", value=datetime.now().date())

        if st.button("💾 保存"):
            add_transaction(
                datetime_str=date_val.strftime("%Y-%m-%d"),
                action=tx_type,
                quantity=1,
                price=amount,
                currency=currency,
                category="支出" if tx_type == "EXPENSE" else "收入",
                subcategory=category,
                target=target,
                note=note,
            )
            st.success("✅ 已保存！")
            st.rerun()

    # ── 月度分析 ──
    raw = get_transactions(limit=500)
    if not raw:
        st.caption("暂无记录")
        return

    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["datetime"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["amount_rmb"] = df.apply(
        lambda x: x["price"] * (
            usd_rmb if x["currency"] == "USD"
            else hkd_rmb if x["currency"] == "HKD"
            else 1
        ), axis=1,
    )

    months = sorted(df["month"].unique(), reverse=True)
    selected = st.selectbox("选择月份", months)
    mdf = df[df["month"] == selected]

    income  = mdf[mdf["action"] == "INCOME"]["amount_rmb"].sum()
    expense = mdf[mdf["action"] == "EXPENSE"]["amount_rmb"].sum()
    net = income - expense

    _metric_row([
        ("💰 本月收入", f"¥{income:,.0f}"),
        ("💸 本月支出", f"¥{expense:,.0f}"),
        ("📊 净积累",   f"¥{net:,.0f}", f"¥{net:,.0f}"),
    ])

    left, right = st.columns(2)

    with left:
        st.subheader("📊 支出分类")
        exp_df = mdf[mdf["action"] == "EXPENSE"]
        if not exp_df.empty:
            grp = exp_df.groupby("subcategory")["amount_rmb"].sum()
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0.4, marker=dict(colors=px.colors.qualitative.Set3),
            ))
            fig.update_layout(**_plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📈 收入分类")
        inc_df = mdf[mdf["action"] == "INCOME"]
        if not inc_df.empty:
            grp = inc_df.groupby("subcategory")["amount_rmb"].sum()
            fig = go.Figure(go.Pie(
                labels=grp.index, values=grp.values,
                hole=0.4, marker=dict(colors=px.colors.qualitative.Pastel),
            ))
            fig.update_layout(**_plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📝 本月明细")
    d = mdf[["date", "action", "subcategory", "price", "currency", "target", "note"]].copy()
    d["date"] = d["date"].dt.strftime("%Y-%m-%d")
    d.columns = ["日期", "类型", "分类", "金额", "币种", "对象", "备注"]
    st.dataframe(d, use_container_width=True)


# ═══════════════════════════════════════════════════════
#  页面：投资组合
# ═══════════════════════════════════════════════════════

def page_portfolio():
    st.title("📈 投资组合 Portfolio")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_rmb:.2f} CNY")

    tx_raw = get_transactions(category="投资", limit=500)
    if not tx_raw:
        st.info("暂无投资数据，去 📝 交易日志 添加吧")
        return

    transactions = [dict_to_transaction(t) for t in tx_raw]
    calc = PortfolioCalculator(transactions)
    summary = calc.get_portfolio_summary()
    holdings = summary.get("holdings", {})

    if not holdings:
        st.info("暂无持仓")
        return

    total_value = sum(h.get("market_value", 0) or h.get("cost_basis", 0) for h in holdings.values())
    total_cost  = sum(h.get("cost_basis", 0) for h in holdings.values())
    total_pnl   = summary["total_unrealized_pnl"]

    _metric_row([
        ("💵 总市值 (USD)", f"${total_value:,.2f}"),
        ("💴 折合人民币",   f"¥{total_value * usd_rmb:,.2f}"),
        ("📊 浮动盈亏",     f"${total_pnl:,.2f}", f"${total_pnl:,.2f}"),
    ])

    # ── 图表 ──
    symbols = list(holdings.keys())
    left, right = st.columns(2)

    with left:
        st.subheader("📊 市值分布")
        vals = [h.get("market_value", 0) or h.get("cost_basis", 0) for h in holdings.values()]
        fig = go.Figure(go.Bar(
            x=symbols, y=vals,
            marker_color=[COLORS["primary"] if v >= 0 else COLORS["danger"] for v in vals],
        ))
        fig.update_layout(**_plotly_layout(xaxis_title="标的", yaxis_title="市值 ($)"))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("📈 盈亏分布")
        pnls = [h.get("unrealized_pnl", 0) for h in holdings.values()]
        fig = go.Figure(go.Bar(
            x=symbols, y=pnls,
            marker_color=[COLORS["secondary"] if p >= 0 else COLORS["danger"] for p in pnls],
        ))
        fig.update_layout(**_plotly_layout(xaxis_title="标的", yaxis_title="盈亏 ($)"))
        st.plotly_chart(fig, use_container_width=True)

    # ── 持仓明细 ──
    st.subheader("📋 持仓明细")
    rows = []
    for sym, h in holdings.items():
        rows.append({
            "标的":     sym,
            "股数":     h.get("current_shares", 0),
            "调整成本": f"${h.get('adjusted_cost', 0):.2f}",
            "权利金":   f"${h.get('total_premiums', 0):,.2f}",
            "期权盈亏": f"${h.get('option_pnl', 0):,.2f}",
            "浮动盈亏": f"${h.get('unrealized_pnl', 0):,.2f}",
            "总盈亏":   f"${h.get('total_pnl', 0):,.2f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ═══════════════════════════════════════════════════════
#  页面：交易日志
# ═══════════════════════════════════════════════════════

TRADE_ACTIONS = [
    "BUY", "SELL",
    "STO (卖Put)", "STO_CALL (卖Call)",
    "BTC (买回平仓)", "BTO_CALL (买Call)",
    "ASSIGNMENT", "DIVIDEND",
]

def page_trading_log():
    st.title("📝 交易日志 Trading Log")
    st.caption("记录每笔投资交易，支持筛选和统计")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ── 新增交易 ──
    with st.expander("➕ 添加交易", expanded=False):
        c1, c2, c3 = st.columns(3)
        symbol   = c1.text_input("标的代码", placeholder="AAPL").upper()
        action   = c2.selectbox("操作", TRADE_ACTIONS)
        date_val = c3.date_input("日期", value=datetime.now().date())

        c4, c5, c6 = st.columns(3)
        quantity = c4.number_input("数量(股/张)", value=100)
        price    = c5.number_input("价格/权利金", value=100.0)
        fees     = c6.number_input("手续费", value=0.0)

        c7, c8 = st.columns(2)
        currency = c7.selectbox("币种", ["USD", "CNY", "HKD"])
        note     = c8.text_input("备注（可选）")

        if st.button("💾 保存交易"):
            action_code = action.split()[0]  # 取第一个单词
            add_transaction(
                datetime_str=date_val.strftime("%Y-%m-%d"),
                action=action_code,
                symbol=symbol,
                quantity=quantity,
                price=price,
                fees=fees,
                currency=currency,
                category="投资",
                note=note,
            )
            st.success("✅ 已保存！")
            st.rerun()

    # ── 交易列表 ──
    tx_raw = get_transactions(category="投资", limit=500)
    if not tx_raw:
        st.caption("暂无交易记录")
        return

    df = pd.DataFrame(tx_raw)
    df["date"] = pd.to_datetime(df["datetime"])

    # 计算实际金额（期权 ×100）
    option_actions = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}
    def _real_amount(row):
        p, q = row["price"], row["quantity"]
        mult = 100 if row["action"] in option_actions else 1
        rate = usd_rmb if row["currency"] == "USD" else (hkd_rmb if row["currency"] == "HKD" else 1)
        return p * q * mult * rate
    df["amount_rmb"] = df.apply(_real_amount, axis=1)

    # 筛选器
    f1, f2 = st.columns(2)
    sym_options = sorted(df["symbol"].dropna().unique().tolist())
    sym_labels  = {s: _stock_label(s) for s in sym_options}
    sym_filter  = f1.selectbox("筛选标的", ["全部"] + [f"{s} {sym_labels[s]}" if sym_labels[s] != s else s for s in sym_options])
    act_labels  = sorted(df["action"].unique().tolist())
    act_filter  = f2.selectbox("筛选操作", ["全部"] + [f"{a} {ACTION_CN.get(a, a)}" for a in act_labels])

    filtered = df.copy()
    if sym_filter != "全部":
        sym_code = sym_filter.split()[0]
        filtered = filtered[filtered["symbol"] == sym_code]
    if act_filter != "全部":
        act_code = act_filter.split()[0]
        filtered = filtered[filtered["action"] == act_code]

    buy_total  = filtered[filtered["action"].isin(["BUY", "ASSIGNMENT"])]["amount_rmb"].sum()
    sell_total = filtered[filtered["action"].isin(["SELL", "CALLED_AWAY"])]["amount_rmb"].sum()
    option_income  = filtered[filtered["action"].isin(["STO", "STO_CALL"])]["amount_rmb"].sum()
    option_expense = filtered[filtered["action"].isin(["STC", "BTC", "BTO_CALL"])]["amount_rmb"].sum()
    fee_total  = filtered["fees"].sum() * usd_rmb

    _metric_row([
        ("💵 股票买入",     f"¥{buy_total:,.0f}"),
        ("💴 股票卖出",     f"¥{sell_total:,.0f}"),
        ("📈 权利金收入",   f"¥{option_income:,.0f}"),
        ("📉 权利金支出",   f"¥{option_expense:,.0f}"),
        ("💸 手续费",       f"¥{fee_total:,.0f}"),
    ])

    st.subheader("📋 交易明细")
    d = filtered[["date", "symbol", "action", "quantity", "price", "fees", "currency", "amount_rmb"]].copy()
    d["date"]   = d["date"].dt.strftime("%Y-%m-%d")
    d["symbol"] = d["symbol"].map(_stock_label)
    d["action"] = d["action"].map(lambda a: ACTION_CN.get(a, a))
    d.columns = ["日期", "标的", "操作", "数量", "单价", "手续费", "币种", "金额(RMB)"]
    st.dataframe(d, use_container_width=True)


# ═══════════════════════════════════════════════════════
#  页面：期权车轮
# ═══════════════════════════════════════════════════════

ACTION_LABELS = {
    "STO":      "卖出 Put",
    "STO_CALL": "卖出 Call",
    "STC":      "买回 Put",
    "BTC":      "买回平仓",
    "BTO_CALL": "买入 Call",
}


def _annualized_return(premium: float, cost_basis: float, days_held: int) -> float:
    """计算年化收益率（%）: (权利金 / 成本) × (365 / 持有天数) × 100"""
    if cost_basis <= 0 or days_held <= 0:
        return 0.0
    return (premium / cost_basis) * (365 / days_held) * 100


def page_wheel():
    st.title("🎯 期权车轮 Options Wheel")
    st.caption("跟踪期权交易：成本基准 · 年化收益 · 回本预测 · 热力图")

    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]

    tx_raw = get_transactions(category="投资", limit=500)
    option_actions = {"STO", "STO_CALL", "STC", "BTC", "BTO_CALL"}
    stock_actions  = {"BUY", "SELL", "ASSIGNMENT", "CALLED_AWAY"}

    # 收集所有做过期权的标的
    option_symbols = sorted(set(
        t["symbol"] for t in tx_raw
        if t.get("action") in option_actions and t.get("symbol")
    ))

    if not option_symbols:
        st.info("暂无期权交易记录，去 📝 交易日志 添加吧！")
        return

    # 全量 Transaction，含股票 + 期权
    all_relevant = [
        t for t in tx_raw
        if t.get("symbol") in option_symbols
        and t.get("action") in (option_actions | stock_actions)
    ]
    transactions = [dict_to_transaction(t) for t in all_relevant]
    wheel_calc = WheelCalculator(transactions)

    # ═══════════════════════════════════════════════════
    #  1️⃣  全标的概览卡片
    # ═══════════════════════════════════════════════════
    st.markdown("### 📊 期权标的总览")

    overview_rows = []
    for sym in option_symbols:
        basis    = wheel_calc.calculate_adjusted_cost_basis(sym)
        premiums = wheel_calc.option_calc.get_premiums_summary(sym)
        shares   = basis.get("current_shares", 0)

        # 找到该标的的第一笔交易日期
        sym_dates = [t["datetime"][:10] for t in all_relevant if t["symbol"] == sym]
        first_date = min(sym_dates) if sym_dates else ""
        days_held  = (datetime.now() - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date else 0

        net_prem   = premiums.get("net_premium", 0)
        cost_basis = basis.get("cost_basis", 0)
        adj_cost   = basis.get("adjusted_cost", 0)

        ann_ret = _annualized_return(net_prem, cost_basis, days_held) if cost_basis > 0 else 0

        overview_rows.append({
            "标的": _stock_label(sym),
            "持仓(股)": int(shares),
            "原始成本/股": f"${cost_basis / shares:.2f}" if shares else "-",
            "调整后成本/股": f"${adj_cost:.2f}" if shares else "-",
            "净权利金": f"${net_prem:,.2f}",
            "累计年化%": f"{ann_ret:.1f}%",
            "持有天数": days_held,
        })

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════
    #  选择标的 → 详细分析
    # ═══════════════════════════════════════════════════
    selected = st.selectbox(
        "选择标的进行详细分析",
        option_symbols,
        format_func=_stock_label,
    )

    basis    = wheel_calc.calculate_adjusted_cost_basis(selected)
    premiums = wheel_calc.option_calc.get_premiums_summary(selected)
    shares   = int(basis.get("current_shares", 0))

    st.markdown(f"### 📈 {_stock_label(selected)} 详细分析")

    # ── 核心指标 ──
    net_prem    = premiums.get("net_premium", 0)
    collected   = premiums.get("total_collected", 0)
    paid        = premiums.get("total_paid", 0)
    cost_basis  = basis.get("cost_basis", 0)
    adj_cost    = basis.get("adjusted_cost", 0)
    total_fees  = sum(t.fees for t in transactions if t.symbol == selected)

    _metric_row([
        ("💵 权利金收入",  f"${collected:,.2f}"),
        ("💸 权利金支出",  f"${paid:,.2f}"),
        ("📈 净权利金",    f"${net_prem:,.2f}"),
        ("💰 调整后成本",  f"${adj_cost:.2f}/股" if shares else "-"),
        ("📉 持仓",        f"{shares} 股"),
    ])

    # ═══════════════════════════════════════════════════
    #  2️⃣  成本基准下降折线图
    # ═══════════════════════════════════════════════════
    sym_txs = sorted(
        [t for t in all_relevant if t["symbol"] == selected],
        key=lambda t: t["datetime"],
    )

    # 逐笔重算成本
    running_stock_cost = 0.0
    running_premium    = 0.0
    running_fees       = 0.0
    running_shares     = 0
    cost_timeline      = []    # [(date, adj_cost_per_share, label)]

    for t in sym_txs:
        action = t["action"]
        qty    = t.get("quantity", 0)
        price  = t.get("price", 0)
        fees   = t.get("fees", 0)
        dt     = t["datetime"][:10]

        if action in ("BUY", "ASSIGNMENT"):
            running_stock_cost += price * qty
            running_shares += qty
        elif action in ("SELL", "CALLED_AWAY"):
            running_stock_cost -= price * qty
            running_shares -= qty
        elif action in option_actions:
            mult = 100
            if action in ("STO", "STO_CALL"):
                running_premium += price * qty * mult   # 收入(降低成本)
            else:
                running_premium -= price * qty * mult   # 支出(增加成本)

        running_fees += fees

        if running_shares > 0:
            adj = (running_stock_cost - running_premium + running_fees) / running_shares
            cost_timeline.append({
                "日期": dt,
                "调整后成本/股": round(adj, 2),
                "操作": ACTION_CN.get(action, action),
            })

    if cost_timeline:
        cdf = pd.DataFrame(cost_timeline)
        st.subheader("📉 成本基准变化")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cdf["日期"], y=cdf["调整后成本/股"],
            mode="lines+markers+text",
            text=[f"${v:.2f}" for v in cdf["调整后成本/股"]],
            textposition="top center",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=10),
            hovertext=cdf["操作"],
        ))
        fig.update_layout(
            **_plotly_layout(height=350),
            yaxis_title="成本/股 ($)",
            xaxis_title="日期",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  3️⃣  每笔期权交易年化收益 + 累计收益曲线
    # ═══════════════════════════════════════════════════
    option_txs = [t for t in sym_txs if t["action"] in option_actions]

    if option_txs and shares > 0:
        # 以第一笔买入日为基准
        stock_buy_dates = [t["datetime"][:10] for t in sym_txs if t["action"] in ("BUY", "ASSIGNMENT")]
        base_date = datetime.strptime(min(stock_buy_dates), "%Y-%m-%d") if stock_buy_dates else datetime.now()
        # 粗略成本基准（不含期权调整）
        raw_stock_cost = sum(
            t["price"] * t["quantity"]
            for t in sym_txs if t["action"] in ("BUY", "ASSIGNMENT")
        )

        trade_details = []
        cumulative_premium = 0.0

        for t in option_txs:
            act   = t["action"]
            qty   = t.get("quantity", 0)
            price = t.get("price", 0)
            fees  = t.get("fees", 0)
            dt    = t["datetime"][:10]

            premium_usd = price * qty * 100
            is_income = act in ("STO", "STO_CALL")
            net_income = premium_usd - fees if is_income else -(premium_usd + fees)
            cumulative_premium += net_income

            days = max((datetime.strptime(dt, "%Y-%m-%d") - base_date).days, 1)
            single_return_pct = (abs(net_income) / raw_stock_cost) * 100 if raw_stock_cost > 0 else 0
            ann_ret = (abs(net_income) / raw_stock_cost) * (365 / days) * 100 if raw_stock_cost > 0 else 0

            trade_details.append({
                "日期": dt,
                "操作": ACTION_CN.get(act, act),
                "张数": qty,
                "权利金/张": f"${price:.2f}",
                "总额(含×100)": f"${premium_usd:,.0f}",
                "手续费": f"${fees:.2f}",
                "净收入": f"${net_income:,.2f}",
                "单笔收益%": f"{single_return_pct:.2f}%" if is_income else f"-{single_return_pct:.2f}%",
                "年化收益%": f"{ann_ret:.1f}%" if is_income else f"-{ann_ret:.1f}%",
                "_cum": cumulative_premium,
                "_date": dt,
            })

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("💹 逐笔交易年化收益")
            display_df = pd.DataFrame(trade_details)[
                ["日期", "操作", "张数", "权利金/张", "总额(含×100)", "手续费", "净收入", "单笔收益%", "年化收益%"]
            ]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        with right_col:
            st.subheader("📈 累计权利金收益曲线")
            cum_df = pd.DataFrame(trade_details)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cum_df["_date"], y=cum_df["_cum"],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color=COLORS["primary"], width=2),
                marker=dict(size=8),
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                **_plotly_layout(height=350),
                yaxis_title="累计净权利金 ($)",
                xaxis_title="日期",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  4️⃣  盈亏分析 & 回本预测
    # ═══════════════════════════════════════════════════
    if shares > 0 and cost_basis > 0:
        st.subheader("🎯 盈亏分析 & 回本预测")

        # 平均每周权利金（基于实际数据）
        if option_txs:
            first_opt_date = datetime.strptime(option_txs[0]["datetime"][:10], "%Y-%m-%d")
            last_opt_date  = datetime.strptime(option_txs[-1]["datetime"][:10], "%Y-%m-%d")
            weeks_active   = max((last_opt_date - first_opt_date).days / 7, 1)
            avg_weekly_prem= net_prem / weeks_active
        else:
            avg_weekly_prem = 0
            weeks_active = 0

        # 回本分析
        if avg_weekly_prem > 0 and shares > 0:
            # 需要降低的总成本 = cost_basis - (stock_original_cost 不做期权时)
            stock_only_cost = sum(
                t["price"] * t["quantity"]
                for t in sym_txs if t["action"] in ("BUY", "ASSIGNMENT")
            )
            already_earned = net_prem
            remaining = stock_only_cost - already_earned  # 到成本=0还需多少
            weeks_to_zero = remaining / avg_weekly_prem if avg_weekly_prem > 0 else float('inf')

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 原始股票成本", f"${stock_only_cost:,.0f}")
            c2.metric("📈 已回收权利金", f"${already_earned:,.2f}")
            c3.metric("📊 每周平均权利金", f"${avg_weekly_prem:,.2f}")
            if weeks_to_zero < 9999:
                c4.metric("⏱️ 预计回本", f"{weeks_to_zero:.0f} 周 ({weeks_to_zero/4.33:.0f} 月)")
            else:
                c4.metric("⏱️ 预计回本", "无法预估")

            # 回本进度条
            progress = min(already_earned / stock_only_cost, 1.0) if stock_only_cost > 0 else 0
            st.progress(progress, text=f"回本进度 {progress*100:.1f}%")

    # ═══════════════════════════════════════════════════
    #  5️⃣  收益率热力图（按月×操作类型）
    # ═══════════════════════════════════════════════════
    if option_txs:
        st.subheader("🗺️ 收益率热力图（月 × 操作类型）")
        heat_rows = []
        for t in option_txs:
            month = t["datetime"][:7]
            act   = ACTION_CN.get(t["action"], t["action"])
            prem  = t["price"] * t["quantity"] * 100
            is_income = t["action"] in ("STO", "STO_CALL")
            heat_rows.append({
                "月份": month,
                "操作": act,
                "金额": prem if is_income else -prem,
            })

        heat_df = pd.DataFrame(heat_rows)
        pivot = heat_df.pivot_table(
            index="操作", columns="月份", values="金额",
            aggfunc="sum", fill_value=0,
        )
        if not pivot.empty:
            fig = go.Figure(go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale=[[0, COLORS["danger"]], [0.5, "#FFFFFF"], [1, COLORS["primary"]]],
                zmid=0,
                text=[[f"${v:,.0f}" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                hovertemplate="月份: %{x}<br>操作: %{y}<br>金额: %{text}<extra></extra>",
            ))
            fig.update_layout(**_plotly_layout(height=300), xaxis_title="月份", yaxis_title="操作类型")
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  6️⃣  操作分布 + 权利金时间线
    # ═══════════════════════════════════════════════════
    df_opt = pd.DataFrame([t for t in all_relevant if t["symbol"] == selected and t["action"] in option_actions])
    if not df_opt.empty:
        df_opt["date"] = pd.to_datetime(df_opt["datetime"])

        left, right = st.columns(2)

        with left:
            st.subheader("📈 权利金时间线")
            df_opt["premium_real"] = df_opt.apply(
                lambda r: r["price"] * r["quantity"] * 100 * (1 if r["action"] in ("STO", "STO_CALL") else -1),
                axis=1,
            )
            monthly = df_opt.groupby(df_opt["date"].dt.strftime("%Y-%m"))["premium_real"].sum()
            if not monthly.empty:
                fig = go.Figure(go.Bar(
                    x=monthly.index, y=monthly.values,
                    marker_color=[COLORS["primary"] if v > 0 else COLORS["danger"] for v in monthly.values],
                    text=[f"${v:,.0f}" for v in monthly.values],
                    textposition="outside",
                ))
                fig.update_layout(**_plotly_layout(height=300), yaxis_title="权利金 ($)")
                st.plotly_chart(fig, use_container_width=True)

        with right:
            st.subheader("📊 操作分布")
            act_counts = df_opt["action"].value_counts()
            fig = go.Figure(go.Pie(
                labels=[ACTION_LABELS.get(a, a) for a in act_counts.index],
                values=act_counts.values,
                hole=0.4,
                marker=dict(colors=[
                    COLORS["primary"], COLORS["danger"], COLORS["warning"],
                    COLORS["secondary"], COLORS["purple"], COLORS["blue_light"],
                ]),
            ))
            fig.update_layout(**_plotly_layout(height=300))
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════
    #  7️⃣  期权交易明细
    # ═══════════════════════════════════════════════════
    st.subheader("📋 期权交易明细")
    if not df_opt.empty:
        d = df_opt[["datetime", "action", "quantity", "price", "fees"]].copy()
        d["日期"]       = pd.to_datetime(d["datetime"]).dt.strftime("%Y-%m-%d")
        d["权利金(总)"] = d["quantity"] * d["price"] * 100
        d["权利金_RMB"] = d["权利金(总)"] * usd_rmb
        d["操作"]       = d["action"].map(ACTION_LABELS).fillna(d["action"])
        d = d[["日期", "操作", "quantity", "price", "权利金(总)", "fees", "权利金_RMB"]]
        d.columns = ["日期", "操作", "张数", "权利金/张(USD)", "权利金(USD)", "手续费", "权利金(RMB)"]
        st.dataframe(d, use_container_width=True, hide_index=True)

    with st.expander("💡 术语说明"):
        st.markdown("""
| 概念 | 说明 | 示例 |
|------|------|------|
| **1 张期权 = 100 股** | 权利金总额 = 单价 × 张数 × 100 | 卖 1 张 $2.60 → 收入 $260 |
| **权利金 (Premium)** | 买卖期权的价格 | STO AAPL 150P → 收 $3.50/股 |
| **行权价 (Strike)** | 到期时约定的买卖价 | Strike = $150 |
| **年化收益率** | (净收入/成本) × (365/天数) | 2天赚0.5% → 年化91.25% |
| **手续费** | 按张计，不乘100 | 1 张手续费 $0.65 |
        """)


# ═══════════════════════════════════════════════════════
#  页面：设置
# ═══════════════════════════════════════════════════════

def page_settings():
    st.title("⚙️ 设置")

    st.subheader("💾 数据备份")
    st.code(
        "scp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/",
        language="bash",
    )

    st.subheader("🗄️ 数据库信息")
    db_path = Path(__file__).parent / "data" / "wealth_v2.db"
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        st.info(f"数据库路径: `{db_path}`\n\n大小: {size_kb:.1f} KB")
    else:
        st.warning("数据库文件不存在")


# ═══════════════════════════════════════════════════════
#  路由 & 主程序
# ═══════════════════════════════════════════════════════

# 页面注册表
PAGES_ASSET = {
    "📊 总览":       page_overview,
    "📅 快照":       page_snapshots,
    "📆 年度":       page_yearly_summary,
    "💸 支出/收入":  page_expense_tracker,
}

PAGES_INVEST = {
    "📈 持仓":       page_portfolio,
    "📝 交易日志":   page_trading_log,
    "🎯 期权车轮":   page_wheel,
}


def main():
    st.set_page_config(**PAGE_CONFIG)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    init_database()

    # ── 侧边栏 ──
    with st.sidebar:
        st.title("💰 财富追踪器")
        st.markdown("---")

        module = st.radio(
            "模块",
            ["🏠 个人资产管理", "📈 投资追踪", "⚙️ 设置"],
            key="main_module",
        )
        st.markdown("---")

        if module == "🏠 个人资产管理":
            page_key = st.selectbox("页面", list(PAGES_ASSET.keys()), key="p1")
        elif module == "📈 投资追踪":
            page_key = st.selectbox("页面", list(PAGES_INVEST.keys()), key="p2")
        else:
            page_key = "⚙️"

        st.markdown("---")
        st.caption("v2.0 · [GitHub](https://github.com/kikojay/option-go)")

    # ── 路由 ──
    all_pages = {**PAGES_ASSET, **PAGES_INVEST, "⚙️": page_settings}
    handler = all_pages.get(page_key, page_overview)
    handler()


if __name__ == "__main__":
    main()
