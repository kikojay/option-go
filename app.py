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
    get_categories_by_type, add_transaction as db_add_transaction
)
from src.calculator import WheelCalculator, PortfolioCalculator
from src.models import Transaction, TransactionType

# 页面配置
st.set_page_config(
    page_title="🎯 Option Wheel Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 现代化样式
st.markdown("""
<style>
    /* 主背景 */
    .stApp {
        background-color: #0E1117;
    }
    /* 标题颜色 */
    h1, h2, h3 {
        color: #00E5FF !important;
        font-weight: 600;
    }
    /* 卡片样式 */
    div.stMetric {
        background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #3D3D5C;
    }
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #161B22;
    }
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #00B8D4 100%);
        color: #000;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    /* 成功消息 */
    .stSuccess {
        background-color: #1B4332;
        border: 1px solid #2D6A4F;
        border-radius: 8px;
    }
    /* 分隔线 */
    hr {
        border-color: #3D3D5C;
    }
    /* 展开框 */
    .streamlit-expanderHeader {
        background-color: #1E1E2E;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化数据库
init_database()


def main():
    """主应用"""
    # 侧边栏
    with st.sidebar:
        st.title("🎯 Wheel Tracker")
        st.markdown("---")
        
        page = st.selectbox(
            "导航",
            ["📊 Dashboard", "📋 交易记录", "📈 Campaigns", "💰 资产", "⚙️ 设置"]
        )
        
        st.markdown("---")
        st.markdown("**快捷链接**")
        st.markdown("- [GitHub](https://github.com/kikojay/option-go)")
        st.markdown("- [文档](#)")

    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📋 交易记录":
        show_transactions()
    elif page == "📈 Campaigns":
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
    portfolio = get_portfolio_summary()

    # 顶部指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💰 净资产",
            f"${portfolio['net_worth']:,.2f}",
            delta_color="normal"
        )

    with col2:
        total_pnl = portfolio['total_realized_pnl'] + portfolio['total_unrealized_pnl']
        st.metric(
            "📈 总盈亏",
            f"${total_pnl:,.2f}",
            delta=f"${portfolio['total_realized_pnl']:,.2f} 已实现"
        )

    with col3:
        st.metric(
            "📦 持仓数",
            len(portfolio['holdings']),
            delta=f"{sum(h.get('shares', 0) for h in portfolio['holdings'].values())} 股"
        )

    with col4:
        if transactions:
            total_premiums = sum(
                -t['amount'] for t in transactions
                if t['subtype'] in ['sell_put', 'sell_call']
            )
            st.metric(
                "💵 权利金总收入",
                f"${total_premiums:,.2f}"
            )
        else:
            st.metric("💵 权利金总收入", "$0.00")

    st.markdown("---")

    # 图表区域
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 持仓分布")
        if portfolio['holdings']:
            holdings = portfolio['holdings']
            symbols = list(holdings.keys())
            shares = [h.get('shares', 0) for h in holdings.values()]
            
            if any(shares):
                fig = go.Figure(data=[go.Pie(
                    labels=symbols,
                    values=shares,
                    hole=0.5,
                    marker=dict(colors=px.colors.qualitative.Set3)
                )])
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="transparent",
                    font=dict(color="white")
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无持仓")

    with col_right:
        st.subheader("💹 盈亏分布")
        if portfolio['holdings']:
            holdings = portfolio['holdings']
            symbols = list(holdings.keys())
            realized = [h.get('realized_pnl', 0) for h in holdings.values()]
            unrealized = [h.get('unrealized_pnl', 0) for h in holdings.values()]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=symbols,
                y=realized,
                name="已实现盈亏",
                marker_color="#00E5FF"
            ))
            fig.add_trace(go.Bar(
                x=symbols,
                y=unrealized,
                name="浮动盈亏",
                marker_color="#FF6B6B"
            ))
            fig.update_layout(
                barmode="group",
                template="plotly_dark",
                paper_bgcolor="transparent",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无盈亏数据")

    # 持仓详情
    st.markdown("---")
    st.subheader("📋 持仓详情")
    
    if portfolio['holdings']:
        for symbol, data in portfolio['holdings'].items():
            with st.expander(f"🎯 {symbol} - {data.get('shares', 0)}股", expanded=True):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("持仓成本", f"${data.get('adjusted_cost', 0):.2f}")
                col_b.metric("市值", f"${data.get('market_value', 0):,.2f}")
                col_c.metric("浮动盈亏", f"${data.get('unrealized_pnl', 0):,.2f}", 
                            delta=f"${data.get('realized_pnl', 0):,.2f}")
                col_d.metric("权利金", f"${data.get('total_premiums', 0):,.2f}")
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
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["amount"] = df["amount"].apply(lambda x: f"${x:,.2f}")
        df["price"] = df["price"].apply(lambda x: f"${x:.2f}" if x else "-")
        
        display_cols = ["date", "symbol", "type", "subtype", "quantity", "price", "amount", "note"]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("暂无交易记录")


def show_campaigns():
    """Campaign 管理"""
    st.title("📈 Campaigns")
    
    # 获取数据
    campaigns = get_campaigns()
    portfolio = get_portfolio_summary()
    holdings = portfolio.get('holdings', {})

    # Campaign 目录
    st.markdown("### 📁 Campaign 目录")
    if campaigns:
        cols = st.columns(len(campaigns) if len(campaigns) < 5 else 4)
        for i, c in enumerate(campaigns):
            symbol = c["symbol"]
            data = holdings.get(symbol, {})
            shares = data.get("shares", 0)
            adj_cost = data.get("adjusted_cost", 0)
            
            with cols[i % 4]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
                    border-radius: 12px;
                    padding: 16px;
                    border: 1px solid #3D3D5C;
                    text-align: center;
                ">
                    <h4 style="margin: 0; color: #00E5FF;">{symbol}</h4>
                    <p style="margin: 8px 0 0 0; color: #888;">{shares}股 | ${adj_cost:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("暂无 Campaign")

    st.markdown("---")

    # 快速添加交易
    with st.expander("⚡ 快速添加交易", expanded=False):
        with st.form("quick_add"):
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                q_symbol = st.text_input("股票代码", placeholder="如 SLV").upper()
            with col_q2:
                q_type = st.selectbox(
                    "类型",
                    ["买入股票", "卖出股票", "卖Put", "买Put平仓", "卖Call", "买Call平仓", "接盘", "被买走"]
                )
            with col_q3:
                q_date = st.date_input("日期", value=datetime.now().date())

            col_q4, col_q5, col_q6 = st.columns(3)
            with col_q4:
                q_price = st.number_input("价格/权利金($)", min_value=0.01, value=100.0, step=0.01)
            with col_q5:
                q_quantity = st.number_input("数量(股/张)", min_value=1, value=100)
            with col_q6:
                q_fees = st.number_input("手续费($)", min_value=0.0, value=0.0, step=0.01)

            # 期权特有字段
            col_qopt1, col_qopt2 = st.columns(2)
            with col_qopt1:
                q_strike = st.number_input("行权价($)", min_value=0.01, value=100.0, step=0.5)
            with col_qopt2:
                q_expiry = st.date_input("到期日", value=None)

            if st.form_submit_button("添加"):
                if q_symbol:
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
                    
                    # 计算方向
                    option_dir = None
                    if db_type == "option":
                        option_dir = -1 if db_subtype.startswith("sell") else 1

                    # 计算金额
                    if db_type == "stock":
                        amount = q_price * q_quantity * (-1 if db_subtype in ["buy", "assignment"] else 1)
                    else:
                        amount = q_price * q_quantity * (-1 if db_subtype.startswith("sell") else 1)

                    tx = Transaction(
                        type=TransactionType(db_type).value,
                        subtype=db_subtype,
                        date=q_date.strftime("%Y-%m-%d"),
                        symbol=q_symbol,
                        quantity=q_quantity,
                        price=q_price,
                        amount=amount,
                        fees=q_fees,
                        strike_price=q_strike if db_type == "option" else None,
                        expiration_date=str(q_expiry) if db_type == "option" and q_expiry else None,
                        option_direction=option_dir
                    )
                    db_add_transaction(tx)
                    st.success(f"✅ 已添加: {q_symbol} {q_type}")
                    st.rerun()

    st.markdown("---")

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

    # 显示 Campaign 详情
    for campaign in campaigns:
        symbol = campaign["symbol"]
        data = holdings.get(symbol, {})
        shares = data.get("shares", 0)
        adj_cost = data.get("adjusted_cost", 0)
        option_pos = data.get("option_positions", {})

        st.markdown("---")
        
        # 标题和状态
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.subheader(f"🎯 {symbol}")
            st.caption(f"状态: {campaign['status']} | 目标: {campaign['target_shares']}股")

        with col2:
            st.metric("持仓", f"{shares}股")
        with col3:
            st.metric("调整后成本", f"${adj_cost:.2f}")
        with col4:
            pnl = data.get('total_pnl', 0)
            st.metric("总盈亏", f"${pnl:,.2f}")

        # 期权仓位
        put_pos = option_pos.get('put', 0)
        call_pos = option_pos.get('call', 0)
        
        if put_pos != 0 or call_pos != 0:
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                put_emoji = "📉" if put_pos < 0 else "📈"
                st.markdown(f"**{put_emoji} Put 仓位**: {put_pos} 张")
            with col_opt2:
                call_emoji = "📉" if call_pos < 0 else "📈"
                st.markdown(f"**{call_emoji} Call 仓位**: {call_pos} 张")

        # Breakeven 倒计时
        if shares > 0:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                avg_premium = st.number_input(
                    f"{symbol} 周均权利金($)",
                    min_value=0.0,
                    value=1.0,
                    key=f"premium_{symbol}",
                    step=0.1
                )
            with col_b2:
                if avg_premium > 0:
                    calc = WheelCalculator([])
                    weeks_data = calc.calculate_breakeven_weeks(
                        symbol,
                        avg_premium,
                        0
                    )
                    if weeks_data["weeks"]:
                        st.info(f"⏱️ 预计还需 **{weeks_data['weeks']:.1f}** 周回本")

        # 交易历史
        tx = get_transactions({"symbol": symbol, "limit": 20})
        if tx:
            with st.expander(f"📝 {symbol} 交易历史"):
                df = pd.DataFrame(tx)
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                df["expiration"] = df["expiration_date"].apply(lambda x: str(x)[:10] if x and str(x) != 'None' else "-")
                df["strike"] = df["strike_price"].apply(lambda x: f"${x:.2f}" if x else "-")
                st.dataframe(
                    df[["date", "subtype", "quantity", "price", "strike", "expiration", "amount"]],
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
        st.info("同步命令：\n\n```bash\nscp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/\n```")

    # 数据导入
    st.subheader("📥 IBKR 导入")
    st.write("上传 IBKR Flex Query XML 文件自动导入交易记录")
    uploaded_file = st.file_uploader("选择文件", type=["xml", "csv"])
    if uploaded_file:
        st.success("文件已上传，处理中...")


# 导入需要的库
import plotly.graph_objects as go
import plotly.express as px


if __name__ == "__main__":
    main()
