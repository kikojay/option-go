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
    usd_to_rmb = rates['USD']['rmb']
    
    # 显示当前汇率
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_to_rmb:.2f} CNY | 1 HKD = ¥{rates['HKD']['rmb']:.2f} CNY")
    
    # 获取数据
    accounts = get_all_accounts()
    portfolio = get_portfolio_summary()
    
    # 计算总资产
    total_usd = sum(a['balance'] for a in accounts if a['currency'] == 'USD')
    total_cny = sum(a['balance'] for a in accounts if a['currency'] == 'CNY')
    total_hkd = sum(a['balance'] for a in accounts if a['currency'] == 'HKD')
    
    total_rmb = total_usd * usd_to_rmb + total_cny + total_hkd * rates['HKD']['rmb']
    
    # 顶部指标（双货币）
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 总资产")
        c1, c2 = st.columns(2)
        c1.metric("美元 (USD)", f"${total_usd:,.0f}")
        c2.metric("人民币 (RMB)", f"¥{total_rmb:,.0f}")
    
    with col2:
        st.subheader("📈 投资组合")
        c3, c4 = st.columns(2)
        c3.metric("市值 (USD)", f"${portfolio['total_value']:,.0f}")
        c4.metric("市值 (RMB)", f"¥{portfolio['total_value'] * usd_to_rmb:,.0f}")
    
    col3, col4 = st.columns(2)
    with col3:
        unrealized = portfolio['total_unrealized']
        st.metric("📉 浮动盈亏 (USD)", f"${unrealized:,.0f}", delta=f"${unrealized:,.0f}")
    with col4:
        unrealized_rmb = unrealized * usd_to_rmb
        st.metric("📊 浮动盈亏 (RMB)", f"¥{unrealized_rmb:,.0f}", delta=f"¥{unrealized_rmb:,.0f}")
    
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
            fig.update_layout(template="plotly_dark", )
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
    st.subheader("🏦 账户详情 (双货币显示)")
    if accounts:
        df = pd.DataFrame(accounts)
        df['余额_RMB'] = df.apply(
            lambda x: x['balance'] * rates[x['currency']]['rmb'] if x['currency'] != 'CNY' else x['balance'],
            axis=1
        )
        # 添加人民币符号
        df['余额_显示'] = df.apply(
            lambda x: f"${x['balance']:,.0f}" if x['currency'] == 'USD' else f"¥{x['balance']:,.0f}" if x['currency'] == 'CNY' else f"${x['balance']:,.0f}",
            axis=1
        )
        
        display_df = df[['name', 'category', 'currency', 'balance', '余额_RMB']].copy()
        display_df.columns = ['账户', '类别', '币种', '原币余额', '折合(RMB)']
        
        st.dataframe(display_df.style.format({
            '折合(RMB)': '¥{:,.0f}'
        }), use_container_width=True)
        
        # 汇总
        total_orig = sum(a['balance'] for a in accounts)
        total_converted = sum(a['balance'] * rates[a['currency']]['rmb'] for a in accounts)
        
        col_acc1, col_acc2 = st.columns(2)
        col_acc1.metric("原币总计", f"${total_orig:,.0f}")
        col_acc2.metric("折合人民币总计", f"¥{total_converted:,.0f}")


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
    """支出/收入追踪"""
    st.title("💸 支出与收入 Tracker")
    st.caption("记录每月收支，分析消费习惯")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    # 添加交易
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
    
    # 获取交易记录
    transactions = get_transactions(limit=500)
    
    if transactions:
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['datetime'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        df['amount_rmb'] = df.apply(
            lambda x: x['price'] * (usd_to_rmb if x['currency'] == 'USD' else 7.8 if x['currency'] == 'HKD' else 1),
            axis=1
        )
        
        # 筛选月份
        months = sorted(df['month'].unique(), reverse=True)
        selected_month = st.selectbox("选择月份", months)
        month_df = df[df['month'] == selected_month]
        
        # 月度汇总
        st.markdown(f"### 📅 {selected_month} 月度汇总")
        
        income = month_df[month_df['action'] == 'INCOME']['amount_rmb'].sum()
        expense = month_df[month_df['action'] == 'EXPENSE']['amount_rmb'].sum()
        net = income - expense
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("💰 本月收入", f"¥{income:,.0f}", delta_color="normal")
        col_m2.metric("💸 本月支出", f"¥{expense:,.0f}", delta_color="inverse")
        col_m3.metric("📊 本月净积累", f"¥{net:,.0f}", delta=f"¥{net:,.0f}")
        
        # 支出分类饼图
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
        
        # 月度趋势图
        st.subheader("📈 月度趋势")
        monthly_summary = df.groupby('month').agg({
            'amount_rmb': lambda x: month_df[month_df['action'] == 'INCOME']['amount_rmb'].sum() if 'INCOME' in x.values else 0
        })
        
        # 正确计算每月收支
        monthly_income = df[df['action'] == 'INCOME'].groupby('month')['amount_rmb'].sum()
        monthly_expense = df[df['action'] == 'EXPENSE'].groupby('month')['amount_rmb'].sum()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(name='收入', x=monthly_income.index, y=monthly_income.values, marker_color='#00E5FF'))
        fig_trend.add_trace(go.Bar(name='支出', x=monthly_expense.index, y=monthly_expense.values, marker_color='#FF6B6B'))
        fig_trend.update_layout(barmode='group', template="plotly_dark", height=350)
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # 交易明细表
        st.subheader("📝 本月交易明细")
        display_df = month_df[['date', 'action', 'subcategory', 'price', 'currency', 'target', 'note']].copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        display_df.columns = ['日期', '类型', '分类', '金额', '币种', '对象', '备注']
        st.dataframe(display_df, use_container_width=True)
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
    
    # 获取汇率
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    cny_to_rmb = 1.0
    
    # 显示当前汇率
    st.info(f"💱 当前汇率: 1 USD = ¥{usd_to_rmb:.2f} CNY")
    
    # 持仓汇总
    portfolio = get_portfolio_summary()
    
    # 双货币统计
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 总市值 (USD)", f"${portfolio['total_value']:,.2f}")
    col2.metric("💴 总市值 (RMB)", f"¥{portfolio['total_value'] * usd_to_rmb:,.2f}")
    col3.metric("📊 浮动盈亏 (USD)", f"${portfolio['total_unrealized']:,.2f}", 
                delta=f"${portfolio['total_unrealized']:,.2f}")
    
    # 双货币详细
    col4, col5, col6 = st.columns(3)
    col4.metric("💵 总成本 (USD)", f"${portfolio['total_cost']:,.2f}")
    col5.metric("💴 总成本 (RMB)", f"¥{portfolio['total_cost'] * usd_to_rmb:,.2f}")
    col6.metric("📊 浮动盈亏 (RMB)", f"¥{portfolio['total_unrealized'] * usd_to_rmb:,.2f}")
    
    # 持仓表格（双货币）
    if portfolio['holdings']:
        df = pd.DataFrame(portfolio['holdings'])
        
        # 添加人民币列
        df['市值_RMB'] = df['market_value'] * usd_to_rmb
        df['成本_RMB'] = df['cost_basis'] * usd_to_rmb
        df['盈亏_RMB'] = df['unrealized_pnl'] * usd_to_rmb
        
        # 颜色
        df['color'] = ['#00E5FF' if v > 0 else '#FF6B6B' for v in df['unrealized_pnl']]
        
        # 图表
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📊 市值分布 (USD)")
            fig = go.Figure(data=[go.Bar(
                x=df['symbol'],
                y=df['market_value'],
                marker_color=df['color']
            )])
            fig.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="市值 ($)")
            st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("📊 市值分布 (RMB)")
            fig2 = go.Figure(data=[go.Bar(
                x=df['symbol'],
                y=df['市值_RMB'],
                marker_color=df['color']
            )])
            fig2.update_layout(template="plotly_dark", xaxis_title="标的", yaxis_title="市值 (¥)")
            st.plotly_chart(fig2, use_container_width=True)
        
        # 详细表格
        st.subheader("📋 持仓明细")
        
        display_df = df[['symbol', 'shares', 'avg_cost', 'cost_basis', 'market_value', 
                         '市值_RMB', 'unrealized_pnl', '盈亏_RMB']].copy()
        display_df.columns = ['标的', '股数', '均价', '成本(USD)', '市值(USD)', '市值(RMB)', '盈亏(USD)', '盈亏(RMB)']
        st.dataframe(display_df.style.format({
            '均价': '${:.2f}',
            '成本(USD)': '${:,.2f}',
            '市值(USD)': '${:,.2f}',
            '市值(RMB)': '¥{:,.2f}',
            '盈亏(USD)': '${:,.2f}',
            '盈亏(RMB)': '¥{:,.2f}'
        }), use_container_width=True)
    
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
    """期权车轮 - 自动从交易日志抓取"""
    st.title("🎯 期权车轮 Options Wheel")
    st.caption("自动从交易日志抓取所有期权交易，按标的分组")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    # 获取所有期权交易
    tx = get_transactions(category='投资', limit=500)
    
    if not tx:
        st.info("暂无期权交易记录，去📝 交易日志添加吧！")
        return
    
    # 筛选期权交易（STO, BTC, STC）
    option_tx = [t for t in tx if t['action'] in ['STO', 'STC', 'BTC']]
    
    if not option_tx:
        st.info("暂无期权交易")
        return
    
    # 按标的分组
    option_df = pd.DataFrame(option_tx)
    option_df['date'] = pd.to_datetime(option_df['datetime'])
    symbols = sorted(option_df['symbol'].dropna().unique())
    
    if not symbols:
        st.info("暂无期权交易")
        return
    
    # 选择查看的标的
    selected_symbol = st.selectbox("选择标的", symbols)
    
    # 该标的的期权交易
    symbol_tx = option_df[option_df['symbol'] == selected_symbol].sort_values('date')
    
    if symbol_tx.empty:
        return
    
    # 计算指标
    sto_tx = symbol_tx[symbol_tx['action'] == 'STO']  # 卖出开仓
    btc_tx = symbol_tx[symbol_tx['action'].isin(['STC', 'BTC'])]  # 买回平仓
    
    total_premium_received = (sto_tx['quantity'] * sto_tx['price']).sum()  # 收到的权利金
    total_premium_paid = (btc_tx['quantity'] * btc_tx['price']).sum()  # 付出的权利金
    net_premium = total_premium_received - total_premium_paid
    
    # 当前持仓
    current_short_put = symbol_tx[symbol_tx['action'] == 'STO']['quantity'].sum()
    current_short_call = 0  # 需要额外逻辑
    
    # 指标卡片
    st.markdown(f"### 📊 {selected_symbol} 期权概览")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💵 累计权利金收入", f"${total_premium_received:,.2f}")
    col2.metric("💸 累计权利金支出", f"${total_premium_paid:,.2f}")
    col3.metric("📈 净权利金", f"${net_premium:,.2f}", delta=f"${net_premium:,.2f}")
    col4.metric("📉 当前空头Put", f"{int(current_short_put)}张")
    
    # 收益图表
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 权利金流向")
        monthly = symbol_tx.groupby(symbol_tx['date'].dt.strftime('%Y-%m'))['price'].sum()
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
        action_counts = symbol_tx['action'].value_counts()
        fig2 = go.Figure(data=[go.Pie(
            labels=action_counts.index,
            values=action_counts.values,
            hole=0.4
        )])
        fig2.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig2, use_container_width=True)
    
    # 交易明细表
    st.subheader("📋 期权交易明细")
    
    display_df = symbol_tx[['datetime', 'action', 'quantity', 'price', 'fees']].copy()
    display_df['date'] = pd.to_datetime(display_df['datetime']).dt.strftime('%Y-%m-%d')
    display_df['权利金_RMB'] = display_df['quantity'] * display_df['price'] * usd_to_rmb
    display_df['操作'] = display_df['action'].map({
        'STO': '卖出Put (开仓)',
        'STC': '买回Put (平仓)',
        'BTC': '买回 (平仓)'
    })
    
    d = display_df[['date', '操作', 'quantity', 'price', 'fees', '权利金_RMB']].copy()
    d.columns = ['日期', '操作', '张数', '权利金(USD)', '手续费', '权利金(RMB)']
    
    st.dataframe(d.style.format({
        '权利金(USD)': '${:,.2f}',
        '手续费': '${:,.2f}',
        '权利金(RMB)': '¥{:,.2f}'
    }), use_container_width=True)
    
    # 实时价格说明
    with st.expander("💡 关于实时价格"):
        st.markdown("""
        **获取实时价格的方式：**
        
        1. **IBKR API** - 需要IBKR账户，支持实时价格
        2. **yfinance** - 免费，延迟15分钟
        3. **券商CSV导入** - 手动导出持仓报告
        
        如需启用实时价格，请提供IBKR API凭证或上传CSV文件。
        """)


def show_trading_log():
    """交易日志"""
    st.title("📝 交易日志 Trading Log")
    st.caption("记录每笔投资交易，支持筛选和统计")
    
    rates = fetch_exchange_rates()
    usd_to_rmb = rates['USD']['rmb']
    
    # 添加交易
    with st.expander("➕ 添加交易", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("标的代码", placeholder="如 AAPL").upper()
        with col2:
            action = st.selectbox(
                "操作", 
                ["BUY", "SELL", "STO (卖Put)", "BTC (买Put平仓)", "STC (卖Call)", "BTC (买Call平仓)", "ASSIGNMENT", "DIVIDEND"]
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
            # 简化 action
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
    
    # 获取交易
    tx = get_transactions(category='投资', limit=200)
    
    if tx:
        df = pd.DataFrame(tx)
        df['date'] = pd.to_datetime(df['datetime'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        df['amount_rmb'] = df['price'] * df['quantity'] * (usd_to_rmb if df['currency'] == 'USD' else 7.8 if df['currency'] == 'HKD' else 1)
        
        # 筛选
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
        
        # 统计
        total_cost = filtered[filtered['action'].isin(['BUY', 'STO'])]['amount_rmb'].sum()
        total_sold = filtered[filtered['action'].isin(['SELL', 'STC', 'BTC', 'ASSIGNMENT'])]['amount_rmb'].sum()
        total_fees = filtered['fees'].sum() * usd_to_rmb
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("💵 总买入/开仓", f"¥{total_cost:,.0f}")
        col_s2.metric("💴 总卖出/平仓", f"¥{total_sold:,.0f}")
        col_s3.metric("💸 手续费总计", f"¥{total_fees:,.0f}")
        
        # 交易明细表
        st.subheader("📋 交易明细")
        
        display_df = filtered[['date', 'symbol', 'action', 'quantity', 'price', 'fees', 'currency', 'note']].copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        display_df['金额_RMB'] = display_df['quantity'] * display_df['price'] * (usd_to_rmb if display_df['currency'] == 'USD' else 7.8 if display_df['currency'] == 'HKD' else 1)
        
        d = display_df[['date', 'symbol', 'action', 'quantity', 'price', 'fees', 'currency', '金额_RMB']].copy()
        d.columns = ['日期', '标的', '操作', '数量', '单价', '手续费', '币种', '金额(RMB)']
        st.dataframe(d, use_container_width=True)


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
        
        # 模块 1：个人资产管理
        st.subheader("🏠 模块1：个人资产管理")
        page1 = st.selectbox(
            "选择子页面",
            ["📊 总览", "📅 快照", "📆 年度", "💸 支出/收入"],
            key="page1"
        )
        
        st.markdown("---")
        
        # 模块 2：投资追踪
        st.subheader("📈 模块2：投资追踪")
        page2 = st.selectbox(
            "选择子页面",
            ["📈 持仓", "📝 交易日志", "🎯 期权车轮"],
            key="page2"
        )
        
        st.markdown("---")
        
        # 设置（单独放）
        st.subheader("⚙️ 设置")
        page3 = st.selectbox(
            "设置",
            ["⚙️ 系统设置"],
            key="page3"
        )
        
        st.markdown("---")
        st.markdown("**GitHub**")
        st.markdown("- [项目地址](https://github.com/kikojay/option-go)")
    
    # 路由
    if page1 == "📊 总览":
        show_overview()
    elif page1 == "📅 快照":
        show_snapshots()
    elif page1 == "📆 年度":
        show_yearly_summary()
    elif page1 == "💸 支出/收入":
        show_expense_tracker()
    elif page2 == "📈 持仓":
        show_portfolio()
    elif page2 == "📝 交易日志":
        show_trading_log()
    elif page2 == "🎯 期权车轮":
        show_wheel()
    elif page3 == "⚙️ 系统设置":
        show_settings()


if __name__ == "__main__":
    main()
