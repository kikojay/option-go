"""
仪表板组件 - Streamlit 页面建筑模块
"""
from typing import Dict, Optional
import streamlit as st
from src.portfolio import PortfolioCalculator, PortfolioAnalyzer
from .charts import (
    plot_cost_basis_over_time,
    plot_pnl_heatmap,
    plot_portfolio_allocation,
    plot_campaign_pnl,
    plot_breakeven_progress
)


class PortfolioDashboard:
    """
    投资组合仪表板
    
    组织和显示完整的投资组合可视化信息。
    """

    def __init__(self, transactions, prices: Optional[Dict] = None):
        """
        初始化仪表板
        
        Args:
            transactions: 交易列表
            prices: 当前价格字典
        """
        self.transactions = transactions
        self.prices = prices or {}
        self.portfolio_calc = PortfolioCalculator(transactions)
        self.portfolio_analyzer = PortfolioAnalyzer(transactions)

    def render_summary_metrics(self):
        """渲染汇总指标行"""
        summary = self.portfolio_calc.get_portfolio_summary(self.prices)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "总市值",
                f"${self.portfolio_calc.get_total_market_value(self.prices):,.2f}"
            )
        
        with col2:
            st.metric(
                "已实现盈亏",
                f"${summary['total_realized_pnl']:,.2f}",
                delta=f"{(summary['total_realized_pnl'] / max(0.01, abs(summary['total_realized_pnl'])) * 100):.1f}%" 
                     if summary['total_realized_pnl'] != 0 else None
            )
        
        with col3:
            st.metric(
                "浮动盈亏",
                f"${summary['total_unrealized_pnl']:,.2f}"
            )
        
        with col4:
            st.metric(
                "总盈亏",
                f"${summary['total_pnl']:,.2f}",
                delta=f"{(summary['total_pnl'] / max(0.01, abs(summary['total_pnl'])) * 100):.1f}%"
                     if summary['total_pnl'] != 0 else None
            )

    def render_allocation(self):
        """渲染资产配置"""
        st.subheader("📊 资产配置")
        summary = self.portfolio_calc.get_portfolio_summary(self.prices)
        
        fig = plot_portfolio_allocation(summary["holdings"])
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    def render_holdings_table(self):
        """渲染持仓表格"""
        st.subheader("💼 持仓详情")
        summary = self.portfolio_calc.get_portfolio_summary(self.prices)
        
        holdings_data = []
        for symbol, holding in summary["holdings"].items():
            holdings_data.append({
                "股票代码": symbol,
                "持仓数": holding.get("current_shares", 0),
                "调整成本": f"${holding.get('adjusted_cost', 0):.2f}",
                "权利金": f"${holding.get('total_premiums', 0):,.2f}",
                "期权盈亏": f"${holding.get('option_pnl', 0):,.2f}",
                "浮动盈亏": f"${holding.get('unrealized_pnl', 0):,.2f}",
                "总盈亏": f"${holding.get('total_pnl', 0):,.2f}"
            })
        
        if holdings_data:
            st.dataframe(holdings_data, use_container_width=True)

    def render_pnl_breakdown(self):
        """渲染盈亏分解"""
        st.subheader("📈 盈亏分解")
        summary = self.portfolio_calc.get_portfolio_summary(self.prices)
        
        col1, col2 = st.columns(2)
        
        for i, (symbol, holding) in enumerate(summary["holdings"].items()):
            if i % 2 == 0:
                col = col1
            else:
                col = col2
            
            with col:
                fig = plot_campaign_pnl(holding)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    def render_analysis(self):
        """渲染分析报告"""
        st.subheader("🔍 分析报告")
        
        analysis = self.portfolio_analyzer.get_performance_summary(self.prices)
        
        # 权利金效率
        st.write("**权利金效率**")
        efficiency = analysis["premium_efficiency"]
        st.write(f"- {efficiency['message']}")
        
        # 多样化
        st.write("**多样化分析**")
        diversification = analysis["diversification"]
        st.write(f"- 持仓品种: {diversification['symbol_count']}")
        st.write(f"- {diversification['recommendation']}")
        
        # 风险
        st.write("**风险指标**")
        risk = analysis["risk"]
        st.write(f"- 最大回撤: {risk.get('max_drawdown_pct', 0):.2f}%")
        st.write(f"- 风险等级: {risk.get('risk_level', '未知')}")

    def render_full_dashboard(self):
        """渲染完整仪表板"""
        st.title("💰 投资组合仪表板")
        
        # 汇总指标
        self.render_summary_metrics()
        
        st.divider()
        
        # 两列布局
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self.render_allocation()
        
        with col2:
            self.render_analysis()
        
        st.divider()
        
        # 持仓表格
        self.render_holdings_table()
        
        st.divider()
        
        # 盈亏图表
        self.render_pnl_breakdown()
