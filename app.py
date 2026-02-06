#!/usr/bin/env python3
"""
Option Wheel Tracker - Streamlit Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加 src 目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.database import (
    init_database, get_transactions, get_campaigns, create_campaign,
    get_portfolio_summary, get_all_accounts, update_daily_price,
    get_categories_by_type
)
from src.calculator import WheelCalculator, PortfolioCalculator
from src.charts import (
    plot_portfolio_allocation, plot_combined_pnl,
    plot_premium_history, plot_breakeven_progress
)

# 页面配置
st.set_page_config(
    page_title="Option Wheel Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 样式
st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 5px;
    }
    .main {
        background-color: #0E0E0E;
    }
    h1, h2, h3 {
        color: #00CED1;
    }
</style>
""", unsafe_allow_html=True)

# 初始化数据库
init_database()


def main():
    """主应用"""

    # 侧边栏
    st.sidebar.title("🎯 Option Wheel Tracker")

    page = st.sidebar.selectbox(
        "导航",
        ["📊 Dashboard", "📋 交易记录", "📈 Campaign", "💰 资产", "⚙️ 设置"]
    )

    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📋 交易记录":
        show_transactions()
    elif page == "📈 Campaign":
        show_campaigns()
    elif page == "💰 资产":
        show_assets()
    elif page == "⚙️ 设置":
        show_settings()


def show_dashboard():
    """仪表盘"""
    st.title("📊 Dashboard")

    # 获取数据
    transactions = get_transactions()
    df_tx = pd.DataFrame(transactions) if transactions else pd.DataFrame()

    # 组合汇总
    portfolio = get_portfolio_summary()

    # 顶部指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "净资产",
            f"${portfolio['net_worth']:,.2f}",
            delta=None
        )

    with col2:
        total_pnl = portfolio['total_realized_pnl'] + portfolio['total_unrealized_pnl']
        st.metric(
            "总盈亏",
            f"${total_pnl:,.2f}",
            delta=f"${portfolio['total_realized_pnl']:,.2f} 已实现"
        )

    with col3:
        st.metric(
            "持仓数",
            len(portfolio['holdings']),
            delta=f"{sum(h['shares'] for h in portfolio['holdings'].values())} 股"
        )

    with col4:
        if transactions:
            total_premiums = sum(
                t['amount'] * -1 for t in transactions
                if t['subtype'] in ['sell_put', 'sell_call']
            )
            st.metric(
                "权利金总收入",
                f"${total_premiums:,.2f}"
            )

    st.divider()

    # 图表区域
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 资产配置")
        if portfolio['holdings']:
            fig = plot_portfolio_allocation(portfolio['holdings'])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无持仓")

    with col_right:
        st.subheader("💹 盈亏分布")
        if portfolio['holdings']:
            fig = plot_combined_pnl(transactions, portfolio['holdings'])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无盈亏数据")

    # 持仓详情
    st.divider()
    st.subheader("📋 持仓详情")

    if portfolio['holdings']:
        for symbol, data in portfolio['holdings'].items():
            with st.expander(f"{symbol} - {data['shares']}股", expanded=True):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("持仓成本", f"${data['avg_cost']:.2f}")
                col_b.metric("市值", f"${data['market_value']:,.2f}")
                col_c.metric("浮动盈亏", f"${data['unrealized_pnl']:,.2f}")
                col_d.metric("已实现盈亏", f"${data.get('realized_pnl', 0):,.2f}")
    else:
        st.info("暂无持仓")


def show_transactions():
    """交易记录"""
    st.title("📋 交易记录")

    # 筛选器
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol_filter = st.selectbox(
            "股票",
            ["全部"] + sorted(list(set(t['symbol'] for t in get_transactions() if t.get('symbol'))))
        )
    with col2:
        type_filter = st.selectbox(
            "类型",
            ["全部", "stock", "option", "expense", "income"]
        )
    with col3:
        limit = st.slider("显示数量", 10, 500, 100)

    # 获取数据
    filters = {"limit": limit}
    if symbol_filter != "全部":
        filters["symbol"] = symbol_filter
    if type_filter != "全部":
        filters["type"] = type_filter

    transactions = get_transactions(filters)
    df = pd.DataFrame(transactions) if transactions else pd.DataFrame()

    # 显示表格
    if not df.empty:
        # 格式化
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["amount"] = df["amount"].apply(lambda x: f"${x:,.2f}")
        df["price"] = df["price"].apply(lambda x: f"${x:.2f}" if x else "-")

        st.dataframe(
            df[["date", "symbol", "type", "subtype", "quantity", "price", "amount", "note"]],
            use_container_width=True
        )
    else:
        st.info("暂无交易记录")


def show_campaigns():
    """Campaign 管理"""
    st.title("📈 Campaign 管理")

    # 快速添加交易（支持任意股票）
    with st.expander("⚡ 快速添加交易（任意股票）", expanded=False):
        with st.form("quick_add"):
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                q_symbol = st.text_input("股票代码", placeholder="如 AAPL").upper()
            with col_q2:
                q_type = st.selectbox(
                    "类型",
                    ["买入股票", "卖出股票", "卖Put", "买Put平仓", "卖Call", "买Call平仓", "接盘", "被买走"]
                )
            with col_q3:
                q_date = st.date_input("日期", value=datetime.now().date())

            col_q4, col_q5, col_q6 = st.columns(3)
            with col_q4:
                q_price = st.number_input("价格($)", min_value=0.01, value=100.0, step=0.01)
            with col_q5:
                q_quantity = st.number_input("数量(股)", min_value=1, value=100)
            with col_q6:
                q_fees = st.number_input("手续费($)", min_value=0.0, value=0.0, step=0.01)

            if st.form_submit_button("添加"):
                if q_symbol:
                    from src.database import add_transaction
                    from src.models import Transaction, TransactionType

                    type_map = {
                        "买入股票": ("stock", "buy"),
                        "卖出股票": ("stock", "sell"),
                        "卖Put": ("option", "sell_put"),
                        "买Put平仓": ("option", "buy_put"),
                        "卖Call": ("option", "sell_call"),
                        "买Call平仓": ("option", "buy_call"),
                        "接盘": ("stock", "assignment"),
                        "被买走": ("stock", "called_away"),
                    }
                    db_type, db_subtype = type_map[q_type]

                    if db_type == "stock":
                        amount = q_price * q_quantity * (-1 if db_subtype in ["buy", "assignment"] else 1)
                    else:
                        amount = q_price * q_quantity * (-1 if db_subtype.startswith("buy") else 1)

                    tx = Transaction(
                        type=TransactionType(db_type).value,
                        subtype=db_subtype,
                        date=q_date.strftime("%Y-%m-%d"),
                        symbol=q_symbol,
                        quantity=q_quantity,
                        price=q_price,
                        amount=amount,
                        fees=q_fees
                    )
                    add_transaction(tx)
                    st.success(f"✅ 已添加: {q_symbol} {q_type}")
                    st.rerun()

    st.divider()

    # 创建新 Campaign
    with st.expander("➕ 创建新 Campaign", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("股票代码", placeholder="如 SLV").upper()
        with col2:
            target_shares = st.number_input("目标股数", min_value=1, value=100)
        with col3:
            if st.button("创建 Campaign"):
                if symbol:
                    create_campaign(symbol, target_shares)
                    st.success(f"✅ 已创建 {symbol} Campaign")
                    st.rerun()

    # 获取 Campaigns
    campaigns = get_campaigns()
    portfolio = get_portfolio_summary()

    # 显示列表
    for campaign in campaigns:
        symbol = campaign["symbol"]
        st.divider()

        # 获取该股票的详情
        symbol_data = portfolio["holdings"].get(symbol, {})

        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.subheader(f"🎯 {symbol}")
            st.caption(f"状态: {campaign['status']} | 目标: {campaign['target_shares']}股")

        with col2:
            shares = symbol_data.get("shares", 0)
            st.metric("当前持仓", f"{shares}股")

        with col3:
            adj_cost = symbol_data.get("avg_cost", 0)
            st.metric("调整后成本", f"${adj_cost:.2f}")

        with col4:
            pnl = symbol_data.get("unrealized_pnl", 0)
            st.metric("浮动盈亏", f"${pnl:,.2f}")

        # Breakeven 倒计时
        if shares > 0:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                avg_premium = st.number_input(
                    f"{symbol} 周均权利金",
                    min_value=0.0,
                    value=1.0,
                    key=f"premium_{symbol}"
                )
            with col_b2:
                if avg_premium > 0:
                    # 计算回本周数
                    calculator = WheelCalculator([])
                    weeks_data = calculator.calculate_breakeven_weeks(
                        symbol,
                        avg_premium * 100,  # 转换为每股
                        0
                    )
                    if weeks_data["weeks"]:
                        st.info(f"⏱️ 预计还需 {weeks_data['weeks']:.1f} 周回本")
                    else:
                        st.info(weeks_data.get("message", ""))

        # 添加交易记录
        with st.expander(f"➕ 添加 {symbol} 交易", expanded=False):
            with st.form(f"add_tx_{symbol}"):
                col_tx1, col_tx2, col_tx3 = st.columns(3)
                with col_tx1:
                    tx_date = st.date_input("日期", value=datetime.now().date(), key=f"date_{symbol}")
                with col_tx2:
                    tx_type = st.selectbox(
                        "类型",
                        ["买入股票", "卖出股票", "卖Put", "买Put平仓", "卖Call", "买Call平仓", "接盘(被行权)", "被买走"],
                        key=f"type_{symbol}"
                    )
                with col_tx3:
                    tx_quantity = st.number_input("数量(股)", min_value=1, value=100, key=f"qty_{symbol}")

                col_tx4, col_tx5, col_tx6 = st.columns(3)
                with col_tx4:
                    tx_price = st.number_input("价格($)", min_value=0.01, value=80.0, step=0.01, key=f"price_{symbol}")
                with col_tx5:
                    tx_fees = st.number_input("手续费($)", min_value=0.0, value=0.0, step=0.01, key=f"fees_{symbol}")
                with col_tx6:
                    tx_note = st.text_input("备注", placeholder="可选", key=f"note_{symbol}")

                submitted = st.form_submit_button("添加记录")
                if submitted:
                    # 根据类型映射到数据库字段
                    type_map = {
                        "买入股票": ("stock", "buy"),
                        "卖出股票": ("stock", "sell"),
                        "卖Put": ("option", "sell_put"),
                        "买Put平仓": ("option", "buy_put"),
                        "卖Call": ("option", "sell_call"),
                        "买Call平仓": ("option", "buy_call"),
                        "接盘(被行权)": ("stock", "assignment"),
                        "被买走": ("stock", "called_away"),
                    }
                    db_type, db_subtype = type_map[tx_type]

                    # 计算总金额
                    if db_type == "stock":
                        amount = tx_price * tx_quantity * (-1 if db_subtype in ["buy", "assignment"] else 1)
                    else:
                        # 期权是每股价格 x 100股
                        amount = tx_price * tx_quantity * (-1 if db_subtype.startswith("buy") else 1)

                    from src.database import add_transaction
                    from src.models import Transaction, TransactionType

                    tx = Transaction(
                        type=TransactionType(db_type).value,
                        subtype=db_subtype,
                        date=tx_date.strftime("%Y-%m-%d"),
                        symbol=symbol,
                        quantity=tx_quantity,
                        price=tx_price,
                        amount=amount,
                        fees=tx_fees,
                        note=tx_note
                    )
                    add_transaction(tx)
                    st.success(f"✅ 已添加: {tx_type} {symbol}")
                    st.rerun()

        # 交易历史
        tx = get_transactions({"symbol": symbol, "limit": 20})
        if tx:
            with st.expander(f"📝 {symbol} 交易历史"):
                df = pd.DataFrame(tx)
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                st.dataframe(
                    df[["date", "subtype", "quantity", "price", "amount"]],
                    use_container_width=True
                )


def show_assets():
    """资产页面"""
    st.title("💰 资产管理")

    # 账户列表
    accounts = get_all_accounts()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("🏦 账户")
        if accounts:
            total = sum(a["balance"] for a in accounts)
            st.metric("总余额", f"${total:,.2f}")

            for acc in accounts:
                st.write(f"- {acc['name']}: ${acc['balance']:,.2f}")
        else:
            st.info("暂无账户")

    with col2:
        st.subheader("📊 支出分类")
        categories = get_categories_by_type("expense")
        if categories:
            for cat in categories[:10]:
                st.write(f"- {cat['name']}")


def show_settings():
    """设置页面"""
    st.title("⚙️ 设置")

    st.info("💡 设置功能开发中...")

    # 备份功能
    st.subheader("💾 备份")
    st.write("点击按钮同步数据到本地：")

    if st.button("同步到 Mac"):
        # 这里可以添加 rsync/scp 命令
        st.info("同步命令示例：\n\n```bash\nscp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/data/*.db ~/Documents/Backup/\n```")

    # 数据导入
    st.subheader("📥 IBKR 导入")
    st.write("上传 IBKR Flex Query XML 文件自动导入交易记录")
    uploaded_file = st.file_uploader("选择文件", type=["xml", "csv"])
    if uploaded_file:
        st.success("文件已上传，处理中...")


if __name__ == "__main__":
    main()
