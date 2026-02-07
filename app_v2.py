#!/usr/bin/env python3
"""
Option Wheel Tracker v2.0 - 基于新架构
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

# 添加 src 目录
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.database_v2 import (
    init_database, get_connection, add_transaction, get_transactions,
    get_all_accounts, create_snapshot, get_latest_snapshot, get_all_snapshots,
    get_yearly_summary, update_yearly_summary, get_strategies,
    get_portfolio_summary, convert_to_rmb, update_exchange_rate
)
from src import (
    Transaction, TransactionType,
    PortfolioCalculator, PortfolioAnalyzer,
    WheelCalculator
)

# ==================== 配置 ====================

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
    return {'USD': {'usd': 1.0, 'rmb': 7.2}, 'CNY': {'usd': 0.14, 'rmb': 1.0}, 'HKD': {'usd': 0.128, 'rmb': 1.0}}


# ==================== 数据转换 ====================

def dict_to_transaction(d: Dict) -> Transaction:
    """将字典转换为 Transaction 对象"""
    # 根据 action 判断类型
    action = d.get('action', '')
    
    if action in ['BUY', 'SELL']:
        tx_type = TransactionType.STOCK
        subtype = 'buy' if action == 'BUY' else 'sell'
    elif action in ['STO', 'STC', 'BTC']:
        tx_type = TransactionType.OPTION
        if action == 'STO':
            subtype = 'sell_put'
        else:
            subtype = 'buy_put'
    elif action == 'EXPENSE':
        tx_type = TransactionType.EXPENSE
        subtype = d.get('subcategory', 'other')
    elif action == 'INCOME':
        tx_type = TransactionType.INCOME
        subtype = d.get('subcategory', 'other')
    else:
        tx_type = TransactionType.STOCK
        subtype = None
    
    return Transaction(
        type=tx_type,
        subtype=subtype,
        date=d.get('datetime', '')[:10],
        amount=d.get('price', 0) * d.get('quantity', 1),
        symbol=d.get('symbol'),
        quantity=d.get('quantity'),
        price=d.get('price'),
        fees=d.get('fees', 0),
        category=d.get('category'),
        note=d.get('note')
    )


# ==================== 页面函数 ====================

def show_overview():
    """总览页面"""
    st.title("📊 总览 Overview")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_to_rmb:.2f} CNY | 1 HKD = ¥{rates['HKD']['rmb']:.2f} CNY")
    
    accounts = get_all_accounts()
    
    total_usd = sum(a['balance'] for a in accounts if a['currency'] == 'USD')
    total_cny = sum(a['balance'] for a in accounts if a['currency'] == 'CNY')
    total_hkd = sum(a['balance'] for a in accounts if a['currency'] == 'HKD')
    
    total_rmb = total_usd * usd_to_rmb + total_cny + total_hkd * rates['HKD']['rmb']
    
    # 投资组合
    tx = get_transactions(category='投资', limit=500)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 总资产")
        c1, c2 = st.columns(2)
        c1.metric("美元 (USD)", f"${total_usd:,.0f}")
        c2.metric("人民币 (RMB)", f"¥{total_rmb:,.0f}")
    
    with col2:
        st.subheader("📈 投资组合")
        # 使用新架构计算
        transactions = [dict_to_transaction(t) for t in tx]
        if transactions:
            calc = PortfolioCalculator(transactions)
            summary = calc.get_portfolio_summary()
            c3, c4 = st.columns(2)
            c3.metric("市值 (USD)", f"${summary['total_unrealized_pnl'] + sum(h.get('cost_basis', 0) for h in summary['holdings'].values()):,.0f}")
            c4.metric("浮动盈亏 (USD)", f"${summary['total_unrealized_pnl']:,.0f}")
        else:
            st.metric("暂无投资数据")
    
    # 资产配置
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🏦 资产配置")
        if accounts:
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
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("📈 投资组合")
        if transactions:
            holdings = summary.get('holdings', {})
            if holdings:
                symbols = list(holdings.keys())
                values = [h.get('cost_basis', 0) for h in holdings.values()]
                fig = go.Figure(data=[go.Bar(
                    x=symbols,
                    y=values,
                    marker_color='#00E5FF'
                )])
                fig.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="成本 ($)")
                st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("🏦 账户详情")
    if accounts:
        df = pd.DataFrame(accounts)
        df['余额_RMB'] = df.apply(
            lambda x: x['balance'] * rates[x['currency']]['rmb'] if x['currency'] != 'CNY' else x['balance'],
            axis=1
        )
        d = df[['name', 'category', 'currency', 'balance', '余额_RMB']].copy()
        d.columns = ['账户', '类别', '币种', '原币余额', '折合(RMB)']
        st.dataframe(d, width='stretch')


def show_snapshots():
    """月度快照"""
    st.title("📅 月度快照 Snapshots")
    
    with st.expander("📝 创建新快照", expanded=False):
        accounts = get_all_accounts()
        rates = fetch_exchange_rates()
        
        if st.button("从当前账户生成快照"):
            total_usd = sum(a['balance'] for a in accounts if a['currency'] == 'USD')
            total_cny = sum(a['balance'] for a in accounts if a['currency'] == 'CNY')
            total_rmb = total_usd * rates['USD']['rmb'] + total_cny
            
            assets_data = {
                'accounts': [{'name': a['name'], 'balance': a['balance'], 'currency': a['currency']} for a in accounts]
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
    
    snapshots = get_all_snapshots()
    
    if snapshots:
        df = pd.DataFrame(snapshots)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['total_assets_rmb'],
            mode='lines+markers',
            name='总资产 (RMB)',
            line=dict(color='#00E5FF', width=2)
        ))
        fig.update_layout(template="plotly_dark", xaxis_title="日期", yaxis_title="资产 (RMB)", hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df[['date', 'total_assets_usd', 'total_assets_rmb', 'note']], width='stretch')


def show_yearly_summary():
    """年度汇总"""
    st.title("📆 年度汇总 Yearly Summary")
    
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
    
    summaries = get_yearly_summary()
    
    if summaries:
        df = pd.DataFrame(summaries)
        
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
        
        st.dataframe(df, width='stretch')


def show_expense_tracker():
    """支出/收入追踪"""
    st.title("💸 支出与收入 Tracker")
    st.caption("记录每月收支，分析消费习惯")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    hkd_to_rmb = rates['HKD']['rmb']
    
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
                ["餐饮", "房租", "交通", "家庭", "外食", "日用", "在家吃饭", "订阅", "工资", "投资", "分红", "其他"]
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
    
    transactions = get_transactions(limit=500)
    
    if transactions:
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['datetime'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        df['amount_rmb'] = df.apply(
            lambda x: x['price'] * (usd_to_rmb if x['currency'] == 'USD' else hkd_to_rmb if x['currency'] == 'HKD' else 1),
            axis=1
        )
        
        months = sorted(df['month'].unique(), reverse=True)
        selected_month = st.selectbox("选择月份", months)
        month_df = df[df['month'] == selected_month]
        
        st.markdown(f"### 📅 {selected_month} 月度汇总")
        
        income = month_df[month_df['action'] == 'INCOME']['amount_rmb'].sum()
        expense = month_df[month_df['action'] == 'EXPENSE']['amount_rmb'].sum()
        net = income - expense
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("💰 本月收入", f"¥{income:,.0f}", delta_color="normal")
        col_m2.metric("💸 本月支出", f"¥{expense:,.0f}", delta_color="inverse")
        col_m3.metric("📊 本月净积累", f"¥{net:,.0f}", delta=f"¥{net:,.0f}")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📊 支出分类")
            expense_df = month_df[month_df['action'] == 'EXPENSE']
            if not expense_df.empty:
                cat_expense = expense_df.groupby('subcategory')['amount_rmb'].sum()
                fig = go.Figure(data=[go.Pie(
                    labels=cat_expense.index,
                    values=cat_expense.values,
                    hole=0.4,
                    marker=dict(colors=px.colors.qualitative.Set3)
                )])
                fig.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("📈 收入分类")
            income_df = month_df[month_df['action'] == 'INCOME']
            if not income_df.empty:
                cat_income = income_df.groupby('subcategory')['amount_rmb'].sum()
                fig2 = go.Figure(data=[go.Pie(
                    labels=cat_income.index,
                    values=cat_income.values,
                    hole=0.4,
                    marker=dict(colors=px.colors.qualitative.Pastel)
                )])
                fig2.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("📝 本月交易明细")
        d = month_df[['date', 'action', 'subcategory', 'price', 'currency', 'target', 'note']].copy()
        d['date'] = d['date'].dt.strftime('%Y-%m-%d')
        d.columns = ['日期', '类型', '分类', '金额', '币种', '对象', '备注']
        st.dataframe(d, width='stretch')


def show_portfolio():
    """投资组合 - 使用新架构"""
    st.title("📈 投资组合 Portfolio")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_to_rmb:.2f} CNY")
    
    # 获取数据并转换
    tx = get_transactions(category='投资', limit=500)
    
    if not tx:
        st.info("暂无投资数据")
        return
    
    # 使用新架构计算
    transactions = [dict_to_transaction(t) for t in tx]
    portfolio_calc = PortfolioCalculator(transactions)
    summary = portfolio_calc.get_portfolio_summary()
    
    holdings = summary.get('holdings', {})
    
    if not holdings:
        st.info("暂无持仓")
        return
    
    # 计算总数
    total_value = sum(h.get('market_value', 0) or h.get('cost_basis', 0) for h in holdings.values())
    total_cost = sum(h.get('cost_basis', 0) for h in holdings.values())
    total_pnl = summary['total_unrealized_pnl']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 总市值 (USD)", f"${total_value:,.2f}")
    col2.metric("💴 总市值 (RMB)", f"¥{total_value * usd_to_rmb:,.2f}")
    col3.metric("📊 浮动盈亏 (USD)", f"${total_pnl:,.2f}", delta=f"${total_pnl:,.2f}")
    
    # 分类映射
    category_map = {
        'CASH': '现金',
        'INDEX': '指数基金',
        'DIVIDEND': '分红股',
        'BLUE': '蓝筹股',
        'METALS': '贵金属',
        'SMALL': '小盘'
    }
    
    # 汇总表
    st.markdown("### 📊 资产大类汇总")
    
    # 简化汇总
    summary_data = {
        '日期': [datetime.now().strftime('%Y-%m-%d')],
        '美元计价总数': [f"${total_value:,.0f}"],
        '总数': [f"¥{total_value * usd_to_rmb:,.0f}"],
        '收益率': [f"{(total_pnl/total_cost*100) if total_cost > 0 else 0:.1f}%"]
    }
    
    for cat_en, cat_cn in category_map.items():
        summary_data[cat_cn] = [f"¥0"]
        summary_data[cat_cn + '%'] = ['0%']
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df.T, width='stretch')
    
    # 可视化
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 市值分布")
        symbols = list(holdings.keys())
        values = [h.get('market_value', 0) or h.get('cost_basis', 0) for h in holdings.values()]
        colors = ['#00E5FF' if v > 0 else '#FF6B6B' for v in values]
        fig = go.Figure(data=[go.Bar(x=symbols, y=values, marker_color=colors)])
        fig.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="市值 ($)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 盈亏分布")
        pnls = [h.get('unrealized_pnl', 0) for h in holdings.values()]
        colors = ['#00E5FF' if p > 0 else '#FF6B6B' for p in pnls]
        fig2 = go.Figure(data=[go.Bar(x=symbols, y=pnls, marker_color=colors)])
        fig2.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="盈亏 ($)")
        st.plotly_chart(fig2, use_container_width=True)
    
    # 持仓明细
    st.markdown("### 📋 持仓明细")
    
    holdings_data = []
    for symbol, h in holdings.items():
        holdings_data.append({
            '标的': symbol,
            '股数': h.get('current_shares', 0),
            '调整成本': f"${h.get('adjusted_cost', 0):.2f}",
            '权利金': f"${h.get('total_premiums', 0):,.2f}",
            '期权盈亏': f"${h.get('option_pnl', 0):,.2f}",
            '浮动盈亏': f"${h.get('unrealized_pnl', 0):,.2f}",
            '总盈亏': f"${h.get('total_pnl', 0):,.2f}"
        })
    
    if holdings_data:
        df = pd.DataFrame(holdings_data)
        st.dataframe(df, width='stretch')


def show_trading_log():
    """交易日志"""
    st.title("📝 交易日志 Trading Log")
    st.caption("记录每笔投资交易，支持筛选和统计")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    hkd_to_rmb = rates['HKD']['rmb']
    
    with st.expander("➕ 添加交易", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("标的代码", placeholder="如 AAPL").upper()
        with col2:
            action = st.selectbox(
                "操作", 
                ["BUY", "SELL", "STO (卖Put)", "STC (卖Call)", "BTC (买回平仓)", "ASSIGNMENT", "DIVIDEND"]
            )
        with col3:
            date_str = st.date_input("日期", value=datetime.now().date())
        
        col4, col5, col6 = st.columns(3)
        with col4:
            quantity = st.number_input("数量(股/张)", value=100)
        with col5:
            price = st.number_input("价格/权利金", value=100.0)
        with col6:
            fees = st.number_input("手续费", value=0.0)
        
        col7, col8 = st.columns(2)
        with col7:
            currency = st.selectbox("币种", ["USD", "CNY", "HKD"])
        with col8:
            note = st.text_input("备注（可选）")
        
        if st.button("保存"):
            action_simple = action.split()[0]
            add_transaction(
                datetime_str=date_str.strftime('%Y-%m-%d'),
                action=action_simple,
                symbol=symbol,
                quantity=quantity,
                price=price,
                fees=fees,
                currency=currency,
                category='投资',
                note=note
            )
            st.success("✅ 已保存！")
            st.rerun()
    
    tx = get_transactions(category='投资', limit=500)
    
    if tx:
        df = pd.DataFrame(tx)
        df['date'] = pd.to_datetime(df['datetime'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        df['amount_rmb'] = df.apply(
            lambda x: x['price'] * x['quantity'] * (usd_to_rmb if x['currency'] == 'USD' else hkd_to_rmb if x['currency'] == 'HKD' else 1),
            axis=1
        )
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            symbol_filter = st.selectbox("筛选标的", ["全部"] + sorted(df['symbol'].dropna().unique().tolist()))
        with col_f2:
            action_filter = st.selectbox("筛选操作", ["全部"] + list(df['action'].unique()))
        
        filtered = df.copy()
        if symbol_filter != "全部":
            filtered = filtered[filtered['symbol'] == symbol_filter]
        if action_filter != "全部":
            filtered = filtered[filtered['action'] == action_filter]
        
        total_cost = filtered[filtered['action'].isin(['BUY', 'STO'])]['amount_rmb'].sum()
        total_sold = filtered[filtered['action'].isin(['SELL', 'STC', 'BTC', 'ASSIGNMENT'])]['amount_rmb'].sum()
        total_fees = filtered['fees'].sum() * usd_to_rmb
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("💵 总买入/开仓", f"¥{total_cost:,.0f}")
        col_s2.metric("💴 总卖出/平仓", f"¥{total_sold:,.0f}")
        col_s3.metric("💸 手续费总计", f"¥{total_fees:,.0f}")
        
        st.subheader("📋 交易明细")
        d = filtered[['date', 'symbol', 'action', 'quantity', 'price', 'fees', 'currency', 'amount_rmb']].copy()
        d['date'] = d['date'].dt.strftime('%Y-%m-%d')
        d.columns = ['日期', '标的', '操作', '数量', '单价', '手续费', '币种', '金额(RMB)']
        st.dataframe(d, width='stretch')


def show_wheel():
    """期权车轮 - 使用新架构"""
    st.title("🎯 期权车轮 Options Wheel")
    st.caption("自动从交易日志抓取期权交易，权利金与行权价分开计算")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    # 获取期权交易
    tx = get_transactions(category='投资', limit=500)
    option_tx = [t for t in tx if t.get('action') in ['STO', 'STC', 'BTC']]
    
    if not option_tx:
        st.info("暂无期权交易记录，去📝 交易日志添加吧！")
        return
    
    # 转换并计算
    transactions = [dict_to_transaction(t) for t in option_tx]
    wheel_calc = WheelCalculator(transactions)
    
    symbols = sorted(set(t.symbol for t in option_tx if t.get('symbol')))
    
    if not symbols:
        st.info("暂无期权交易")
        return
    
    selected_symbol = st.selectbox("选择标的", symbols)
    
    # 计算指标
    basis = wheel_calc.calculate_adjusted_cost_basis(selected_symbol)
    option_pnl = wheel_calc.calculate_option_pnl(selected_symbol)
    
    # 指标卡片
    st.markdown(f"### 📊 {selected_symbol} 期权概览")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 权利金收入", f"${option_pnl.get('total_premiums', 0):,.2f}")
    col2.metric("💸 权利金支出", f"${abs(option_pnl.get('total_premiums', 0) - option_pnl.get('net_pnl', 0)):,.2f}")
    col3.metric("📈 净权利金", f"${option_pnl.get('net_pnl', 0):,.2f}", delta=f"${option_pnl.get('net_pnl', 0):,.2f}")
    
    col4, col5 = st.columns(2)
    col4.metric("💰 调整后成本", f"${basis.get('adjusted_cost', 0):.2f}")
    col5.metric("📉 当前持仓", f"{int(basis.get('current_shares', 0))}股")
    
    # 可视化
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 权利金流向")
        df = pd.DataFrame(option_tx)
        df['date'] = pd.to_datetime(df['datetime'])
        monthly = df.groupby(df['date'].dt.strftime('%Y-%m'))['price'].sum()
        if not monthly.empty:
            fig = go.Figure(data=[go.Bar(
                x=monthly.index,
                y=monthly.values,
                marker_color=['#00E5FF' if v > 0 else '#FF6B6B' for v in monthly.values]
            )])
            fig.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("📊 操作类型分布")
        action_counts = df['action'].value_counts()
        fig2 = go.Figure(data=[go.Pie(
            labels=action_counts.index,
            values=action_counts.values,
            hole=0.4,
            marker=dict(colors=px.colors.qualitative.Set3)
        )])
        fig2.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig2, use_container_width=True)
    
    # 交易明细
    st.subheader("📋 期权交易明细")
    d = df[['datetime', 'action', 'quantity', 'price', 'fees']].copy()
    d['日期'] = pd.to_datetime(d['datetime']).dt.strftime('%Y-%m-%d')
    d['权利金_RMB'] = d['quantity'] * d['price'] * usd_to_rmb
    action_map = {'STO': '卖出Put', 'STC': '买回Put', 'BTC': '买回平仓'}
    d['操作'] = d['action'].map(action_map)
    d = d[['日期', '操作', 'quantity', 'price', 'fees', '权利金_RMB']]
    d.columns = ['日期', '操作', '张数', '权利金(USD)', '手续费', '权利金(RMB)']
    st.dataframe(d, width='stretch')
    
    with st.expander("💡 权利金与行权价的区别"):
        st.markdown("""
        | 概念 | 说明 | 记录位置 |
        |------|------|----------|
        | **权利金 (Premium)** | 买卖期权的价格 | price 字段 |
        | **行权价 (Strike)** | 期权到期时可以买卖股票的约定价格 | note 字段 |
        """)


def show_settings():
    """设置"""
    st.title("⚙️ 设置")
    
    st.subheader("💾 备份")
    st.info("同步命令：\n\n```bash\nscp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/\n```")


# ==================== 主程序 ====================

def main():
    """主应用"""
    with st.sidebar:
        st.title("💰 财富追踪器")
        st.markdown("---")
        
        # 选择大模块
        module = st.radio(
            "选择模块",
            ["🏠 个人资产管理", "📈 投资追踪", "⚙️ 设置"],
            index=0,
            key="main_module"
        )
        
        st.markdown("---")
        
        # 子页面选择
        if module == "🏠 个人资产管理":
            page = st.selectbox(
                "选择页面",
                ["📊 总览", "📅 快照", "📆 年度", "💸 支出/收入"],
                key="sub_page1"
            )
        elif module == "📈 投资追踪":
            page = st.selectbox(
                "选择页面",
                ["📈 持仓", "📝 交易日志", "🎯 期权车轮"],
                key="sub_page2"
            )
        else:
            page = "⚙️ 系统设置"
        
        st.markdown("---")
        st.markdown("**GitHub**: [项目地址](https://github.com/kikojay/option-go)")
    
    # 路由
    if page == "📊 总览":
        show_overview()
    elif page == "📅 快照":
        show_snapshots()
    elif page == "📆 年度":
        show_yearly_summary()
    elif page == "💸 支出/收入":
        show_expense_tracker()
    elif page == "📈 持仓":
        show_portfolio()
    elif page == "📝 交易日志":
        show_trading_log()
    elif page == "🎯 期权车轮":
        show_wheel()
    elif page == "⚙️ 系统设置":
        show_settings()


if __name__ == "__main__":
    main()
