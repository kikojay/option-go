#!/usr/bin/env python3
"""
Option Wheel Tracker v2.0 - Personal Finance & Investment Management
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

# 添加 src 目录
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.database_v2 import (
    init_database, get_connection, add_transaction, get_transactions,
    get_all_accounts, create_snapshot, get_latest_snapshot, get_all_snapshots,
    get_yearly_summary, update_yearly_summary, get_strategies,
    get_portfolio_summary, convert_to_rmb, update_exchange_rate
)

# ==================== 配置 ====================

# 页面配置
st.set_page_config(
    page_title="💰 财富追踪器",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 样式
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00E5FF !important; font-weight: 600; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #3D3D5C;
    }
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #00B8D4 100%);
        color: #000;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] { background-color: #161B22; }
</style>
""", unsafe_allow_html=True)

# 初始化数据库
init_database()


# ==================== 汇率服务 ====================

@st.cache_data(ttl=3600)
def fetch_exchange_rates() -> Dict:
    """获取汇率"""
    try:
        # 使用免费汇率 API
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rates = {
                'USD': {'usd': 1.0, 'rmb': data['rates'].get('CNY', 7.2)},
                'CNY': {'usd': 1/data['rates'].get('CNY', 7.2), 'rmb': 1.0},
                'HKD': {'usd': 1/7.8, 'rmb': 1/0.98}
            }
            return rates
    except:
        pass
    # 默认汇率
    return {'USD': {'usd': 1.0, 'rmb': 7.2}, 'CNY': {'usd': 0.14, 'rmb': 1.0}, 'HKD': {'usd': 0.128, 'rmb': 1.0}}


# ==================== 页面函数 ====================

def show_overview():
    """总览页面"""
    st.title("📊 总览 Overview")
    
    # 获取汇率
    rates = fetch_exchange_rates()
    
    # 获取数据
    accounts = get_all_accounts()
    snapshot = get_latest_snapshot()
    portfolio = get_portfolio_summary()
    
    # 计算总资产
    total_usd = sum(a['balance'] for a in accounts if a['currency'] == 'USD')
    total_cny = sum(a['balance'] for a in accounts if a['currency'] == 'CNY')
    total_hkd = sum(a['balance'] for a in accounts if a['currency'] == 'HKD')
    
    total_rmb = total_usd * rates['USD']['rmb'] + total_cny + total_hkd * rates['HKD']['rmb']
    
    # 顶部指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 总资产 (RMB)", f"¥{total_rmb:,.0f}")
    with col2:
        portfolio_value = portfolio['total_value']
        st.metric("📈 投资组合", f"${portfolio_value:,.0f}")
    with col3:
        unrealized = portfolio['total_unrealized']
        st.metric("📉 浮动盈亏", f"${unrealized:,.0f}", delta=f"${unrealized:,.0f}")
    with col4:
        st.metric("💵 USD 资产", f"${total_usd:,.0f}")
    
    # 资产配置饼图
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🏦 资产配置")
        
        # 按类别汇总
        category_assets = {}
        for a in accounts:
            cat = a['category']
            amount = a['balance']
            if a['currency'] == 'USD':
                amount *= rates['USD']['rmb']
            elif a['currency'] == 'HKD':
                amount *= rates['HKD']['rmb']
            category_assets[cat] = category_assets.get(cat, 0) + amount
        
        if category_assets:
            fig = go.Figure(data=[go.Pie(
                labels=list(category_assets.keys()),
                values=list(category_assets.values()),
                hole=0.5,
                marker=dict(colors=px.colors.qualitative.Set3)
            )])
            fig.update_layout(template="plotly_dark", paper_bgcolor="transparent")
            st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("📈 投资组合")
        if portfolio['holdings']:
            df = pd.DataFrame(portfolio['holdings'])
            fig = go.Figure(data=[go.Bar(
                x=df['symbol'],
                y=df['market_value'],
                marker_color=['#00E5FF' if v > 0 else '#FF6B6B' for v in df['unrealized_pnl']]
            )])
            fig.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="市值 ($)")
            st.plotly_chart(fig, use_container_width=True)
    
    # 账户详情
    st.subheader("🏦 账户详情")
    if accounts:
        df = pd.DataFrame(accounts)
        df['balance_rmb'] = df.apply(
            lambda x: x['balance'] * rates[x['currency']]['rmb'] if x['currency'] != 'CNY' else x['balance'],
            axis=1
        )
        st.dataframe(
            df[['name', 'category', 'currency', 'balance', 'balance_rmb']],
            use_container_width=True
        )


def show_snapshots():
    """月度快照"""
    st.title("📅 月度快照 Snapshots")
    
    # 创建新快照
    with st.expander("📝 创建新快照", expanded=False):
        accounts = get_all_accounts()
        rates = fetch_exchange_rates()
        
        if st.button("从当前账户生成快照"):
            total_usd = sum(a['balance'] for a in accounts if a['currency'] == 'USD')
            total_cny = sum(a['balance'] for a in accounts if a['currency'] == 'CNY')
            total_rmb = total_usd * rates['USD']['rmb'] + total_cny
            
            assets_data = {
                'accounts': [{'name': a['name'], 'balance': a['balance'], 'currency': a['currency']} for a in accounts],
                'portfolio': get_portfolio_summary()
            }
            
            create_snapshot(
                date_str=datetime.now().strftime('%Y-%m-%d'),
                total_assets_usd=total_usd,
                total_assets_rmb=total_rmb,
                assets_data=assets_data,
                note="自动生成"
            )
            st.success("✅ 快照已创建！")
            st.rerun()
    
    # 历史快照
    snapshots = get_all_snapshots()
    
    if snapshots:
        st.subheader("📜 历史快照")
        
        # 曲线图
        df = pd.DataFrame(snapshots)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['total_assets_rmb'],
            mode='lines+markers',
            name='总资产 (RMB)',
            line=dict(color='#00E5FF', width=2)
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="日期",
            yaxis_title="资产 (RMB)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 表格
        st.dataframe(
            df[['date', 'total_assets_usd', 'total_assets_rmb', 'note']],
            use_container_width=True
        )


def show_yearly_summary():
    """年度汇总"""
    st.title("📆 年度汇总 Yearly Summary")
    
    # 更新/添加年度数据
    with st.expander("➕ 添加/更新年度数据", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            year = st.number_input("年份", min_value=2020, max_value=2030, value=datetime.now().year)
        with col2:
            pre_tax = st.number_input("税前收入", value=0.0)
        with col3:
            social = st.number_input("五险一金", value=0.0)
        with col4:
            tax = st.number_input("个人所得税", value=0.0)
        
        col5, col6 = st.columns(2)
        with col5:
            investment = st.number_input("理财收入", value=0.0)
        with col6:
            note = st.text_input("备注")
        
        if st.button("保存"):
            update_yearly_summary(year, pre_tax, social, tax, investment, note)
            st.success("✅ 已保存！")
            st.rerun()
    
    # 显示年度汇总
    summaries = get_yearly_summary()
    
    if summaries:
        df = pd.DataFrame(summaries)
        
        # 图表
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📈 收入对比")
            fig = go.Figure(data=[
                go.Bar(name='税前', x=df['year'], y=df['pre_tax_income'], marker_color='#00E5FF'),
                go.Bar(name='税后', x=df['year'], y=df['post_tax_income'], marker_color='#4ECDC4')
            ])
            fig.update_layout(barmode='group', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("📊 支出明细")
            fig = go.Figure(data=[
                go.Bar(name='五险一金', x=df['year'], y=df['social_insurance'], marker_color='#FF6B6B'),
                go.Bar(name='个税', x=df['year'], y=df['income_tax'], marker_color='#FFE66D')
            ])
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        
        # 表格
        st.subheader("📋 年度明细")
        st.dataframe(df, use_container_width=True)


def show_expense_tracker():
    """支出追踪"""
    st.title("💸 支出追踪 Expense Tracker")
    
    # 添加支出/收入
    with st.expander("➕ 记一笔", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            tx_type = st.selectbox("类型", ["EXPENSE", "INCOME"])
        with col2:
            amount = st.number_input("金额", value=0.0)
        with col3:
            currency = st.selectbox("币种", ["USD", "CNY", "HKD"])
        
        col4, col5, col6 = st.columns(3)
        with col4:
            category = st.selectbox(
                "分类",
                ["餐饮", "房租", "交通", "家庭", "外食", "日用", "在家吃饭", "订阅", "工资", "投资", "其他"]
            )
        with col5:
            subcategory = st.text_input("子分类（可选）")
        with col6:
            target = st.text_input("对象（可选）")
        
        col7, col8 = st.columns(2)
        with col7:
            note = st.text_input("备注")
        with col8:
            date_str = st.date_input("日期", value=datetime.now().date())
        
        if st.button("保存"):
            add_transaction(
                datetime_str=date_str.strftime('%Y-%m-%d'),
                action=tx_type,
                quantity=1,
                price=amount,
                currency=currency,
                category='支出' if tx_type == 'EXPENSE' else '收入',
                subcategory=category,
                target=target,
                note=note
            )
            st.success("✅ 已保存！")
            st.rerun()
    
    # 显示交易记录
    st.subheader("📝 交易记录")
    transactions = get_transactions(limit=200)
    
    if transactions:
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
        
        # 筛选
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            filter_type = st.selectbox("筛选类型", ["全部", "EXPENSE", "INCOME"])
        with col_filter2:
            filter_cat = st.selectbox("筛选分类", ["全部"] + list(df['subcategory'].dropna().unique()))
        
        if filter_type != "全部":
            df = df[df['action'] == filter_type]
        if filter_cat != "全部":
            df = df[df['subcategory'] == filter_cat]
        
        # 统计
        if not df.empty:
            income = df[df['action'] == 'INCOME']['price'].sum()
            expense = df[df['action'] == 'EXPENSE']['price'].sum()
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("总收入", f"${income:,.2f}")
            col_stat2.metric("总支出", f"${expense:,.2f}")
            col_stat3.metric("净积累", f"${income - expense:,.2f}")
        
        st.dataframe(df[['date', 'action', 'subcategory', 'price', 'currency', 'target', 'note']], use_container_width=True)


def show_portfolio():
    """投资组合"""
    st.title("📈 投资组合 Portfolio")
    
    # 持仓汇总
    portfolio = get_portfolio_summary()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总市值", f"${portfolio['total_value']:,.2f}")
    col2.metric("总成本", f"${portfolio['total_cost']:,.2f}")
    col3.metric("浮动盈亏", f"${portfolio['total_unrealized']:,.2f}", 
                delta=f"${portfolio['total_unrealized']:,.2f}")
    
    # 持仓表格
    if portfolio['holdings']:
        df = pd.DataFrame(portfolio['holdings'])
        
        # 添加颜色
        df['color'] = ['#00E5FF' if v > 0 else '#FF6B6B' for v in df['unrealized_pnl']]
        
        fig = go.Figure(data=[go.Bar(
            x=df['symbol'],
            y=df['market_value'],
            marker_color=df['color']
        )])
        fig.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="市值")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df, use_container_width=True)
    
    # 添加交易
    with st.expander("➕ 记录交易", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("标的代码", placeholder="如 AAPL").upper()
        with col2:
            action = st.selectbox("操作", ["BUY", "SELL", "STO", "BTC"])
        with col3:
            quantity = st.number_input("数量", value=100)
        
        col4, col5, col6 = st.columns(3)
        with col4:
            price = st.number_input("价格", value=100.0)
        with col5:
            fees = st.number_input("手续费", value=0.0)
        with col6:
            date_str = st.date_input("日期", value=datetime.now().date())
        
        if st.button("保存"):
            add_transaction(
                datetime_str=date_str.strftime('%Y-%m-%d'),
                action=action,
                symbol=symbol,
                quantity=quantity,
                price=price,
                fees=fees,
                category='投资'
            )
            st.success("✅ 已保存！")
            st.rerun()
    
    # 交易记录
    st.subheader("📝 交易日志")
    tx = get_transactions(category='投资', limit=100)
    if tx:
        df = pd.DataFrame(tx)
        df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
        st.dataframe(df[['date', 'symbol', 'action', 'quantity', 'price', 'fees']], use_container_width=True)


def show_wheel():
    """期权车轮"""
    st.title("🎯 期权车轮 Options Wheel")
    
    strategies = get_strategies(status='active')
    
    # 创建策略
    with st.expander("➕ 创建策略", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("策略名称")
        with col2:
            symbol = st.text_input("标的代码").upper()
        with col3:
            strategy_type = st.selectbox("类型", ["wheel", "income", "speculation"])
        
        if st.button("创建"):
            from src.database_v2 import create_strategy
            create_strategy(name, strategy_type, symbol)
            st.success("✅ 已创建！")
            st.rerun()
    
    # 显示策略
    for s in strategies:
        st.markdown(f"### {s['name']} ({s['symbol']})")
        st.caption(f"类型: {s['type']} | 状态: {s['status']}")
        
        # 获取该标的交易
        tx = get_transactions(symbol=s['symbol'], limit=50)
        
        if tx:
            # 计算累计权利金
            premiums = sum(
                t['quantity'] * t['price'] 
                for t in tx 
                if t['action'] in ['STO', 'BTC']
            )
            
            col1, col2, col3 = st.columns(3)
            col1.metric("累计权利金", f"${premiums:,.2f}")
            
            st.dataframe(pd.DataFrame(tx)[['date', 'action', 'quantity', 'price']], use_container_width=True)


def show_settings():
    """设置"""
    st.title("⚙️ 设置")
    
    st.subheader("💾 备份")
    st.info("同步命令：\n\n```bash\nscp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/\n```")
    
    st.subheader("📥 导入")
    uploaded = st.file_uploader("上传交易 CSV", type=["csv"])
    if uploaded:
        st.success("文件已上传，处理中...")


# ==================== 主程序 ====================

def main():
    """主应用"""
    # 侧边栏导航
    with st.sidebar:
        st.title("💰 财富追踪器")
        st.markdown("---")
        
        page = st.selectbox(
            "导航",
            ["📊 总览", "📅 快照", "📆 年度", "💸 支出", "📈 投资组合", "🎯 期权车轮", "⚙️ 设置"]
        )
        
        st.markdown("---")
        st.markdown("**快捷链接**")
        st.markdown("- [GitHub](https://github.com/kikojay/option-go)")
    
    # 路由
    if page == "📊 总览":
        show_overview()
    elif page == "📅 快照":
        show_snapshots()
    elif page == "📆 年度":
        show_yearly_summary()
    elif page == "💸 支出":
        show_expense_tracker()
    elif page == "📈 投资组合":
        show_portfolio()
    elif page == "🎯 期权车轮":
        show_wheel()
    elif page == "⚙️ 设置":
        show_settings()


if __name__ == "__main__":
    main()
