"""
可视化模块 - 图表和仪表板

使用 Plotly 和 Streamlit 进行数据可视化
"""

# 注意：charts 和 dashboards 模块可选导入，避免在不需要时加载重型依赖

def get_chart_functions():
    """动态导入chart函数"""
    from .charts import (
        plot_cost_basis_over_time,
        plot_pnl_heatmap,
        plot_portfolio_allocation,
        plot_campaign_pnl,
        plot_breakeven_progress,
        plot_premium_history,
        plot_combined_pnl
    )
    return {
        'plot_cost_basis_over_time': plot_cost_basis_over_time,
        'plot_pnl_heatmap': plot_pnl_heatmap,
        'plot_portfolio_allocation': plot_portfolio_allocation,
        'plot_campaign_pnl': plot_campaign_pnl,
        'plot_breakeven_progress': plot_breakeven_progress,
        'plot_premium_history': plot_premium_history,
        'plot_combined_pnl': plot_combined_pnl,
    }

def get_dashboard_class():
    """动态导入仪表板类"""
    from .dashboards import PortfolioDashboard
    return PortfolioDashboard

__all__ = [
    'get_chart_functions',
    'get_dashboard_class',
]
