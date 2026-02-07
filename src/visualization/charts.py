"""
图表绘制模块 - 使用 Plotly 生成交互式图表
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict
from src.options import WheelStrategyCalculator


def plot_cost_basis_over_time(transactions: List[Dict]) -> go.Figure:
    """
    绘制持仓成本随时间变化的折线图
    """
    if not transactions:
        return None

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # 简化版：直接绘制交易时间线
    fig = go.Figure()

    # 添加成本基准线
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["adjusted_cost"] if "adjusted_cost" in df.columns else [],
        mode="lines+markers",
        name="Adjusted Cost Basis",
        line=dict(color="#00CED1", width=2)
    ))

    fig.update_layout(
        title="Adjusted Cost Basis Over Time",
        xaxis_title="Date",
        yaxis_title="Cost per Share ($)",
        template="plotly_dark",
        hovermode="x unified"
    )

    return fig


def plot_pnl_heatmap(transactions: List[Dict]) -> go.Figure:
    """
    绘制收益率热力图
    """
    if not transactions:
        return None

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    # 计算月度收益率
    monthly_returns = df.groupby(["symbol", "month"]).agg({
        "amount": "sum",
        "quantity": "sum"
    }).reset_index()

    if monthly_returns.empty:
        return None

    # 透视表
    pivot = monthly_returns.pivot_table(
        index="symbol",
        columns="month",
        values="amount",
        fill_value=0
    )

    fig = px.imshow(
        pivot,
        labels=dict(x="Month", y="Symbol", color="P&L ($)"),
        color_continuous_scale="RdYlGn",
        template="plotly_dark"
    )

    fig.update_layout(
        title="Monthly P&L Heatmap",
        xaxis_title="Month",
        yaxis_title="Symbol"
    )

    return fig


def plot_portfolio_allocation(holdings: Dict[str, Dict]) -> go.Figure:
    """
    绘制资产配置饼图
    """
    if not holdings:
        return None

    labels = list(holdings.keys())
    values = [h.get("market_value", h.get("total_cost", 0)) for h in holdings.values()]

    # 过滤掉0值
    nonzero = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not nonzero:
        return None

    labels, values = zip(*nonzero)

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=px.colors.qualitative.Set3)
    )])

    fig.update_layout(
        title="Portfolio Allocation",
        template="plotly_dark"
    )

    return fig


def plot_campaign_pnl(campaign_data: Dict) -> go.Figure:
    """
    绘制单个 Campaign 的 P&L 分解图
    """
    realized = campaign_data.get("option_pnl", 0)
    unrealized = campaign_data.get("unrealized_pnl", 0)

    fig = go.Figure(data=[go.Bar(
        x=["Option P&L", "Unrealized P&L", "Total P&L"],
        y=[realized, unrealized, realized + unrealized],
        marker_color=["#00CED1", "#FF6B6B", "#4ECDC4"]
    )])

    fig.update_layout(
        title=f"{campaign_data.get('symbol', 'Campaign')} P&L Breakdown",
        yaxis_title="P&L ($)",
        template="plotly_dark"
    )

    return fig


def plot_breakeven_progress(current_cost: float, start_cost: float, target_cost: float = 0) -> go.Figure:
    """
    绘制回本进度条
    """
    total_progress = start_cost - target_cost
    current_progress = start_cost - current_cost
    pct = (current_progress / total_progress * 100) if total_progress > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        title={"text": "Breakeven Progress"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#00CED1"},
            "steps": [
                {"range": [0, 50], "color": "#FF6B6B"},
                {"range": [50, 100], "color": "#4ECDC4"}
            ],
            "threshold": {
                "line": {"color": "white", "width": 4},
                "thickness": 0.75,
                "value": pct
            }
        }
    ))

    fig.update_layout(template="plotly_dark")

    return fig


def plot_premium_history(transactions: List[Dict]) -> go.Figure:
    """
    绘制权利金收入历史
    """
    df = pd.DataFrame(transactions)
    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    premiums = df[df["subtype"].isin(["sell_put", "sell_call"])]

    if premiums.empty:
        return None

    fig = px.bar(
        premiums,
        x="date",
        y="amount",
        color="subtype",
        title="Premium Income Over Time",
        template="plotly_dark"
    )

    return fig


def plot_combined_pnl(transactions: List[Dict], holdings: Dict[str, Dict]) -> go.Figure:
    """
    绘制综合盈亏图（Option P&L + Unrealized）
    """
    fig = go.Figure()

    symbols = list(holdings.keys())
    option_pnl = [holdings[s].get("option_pnl", 0) for s in symbols]
    unrealized = [holdings[s].get("unrealized_pnl", 0) for s in symbols]

    fig.add_trace(go.Bar(
        x=symbols,
        y=option_pnl,
        name="Option P&L",
        marker_color="#00CED1"
    ))

    fig.add_trace(go.Bar(
        x=symbols,
        y=unrealized,
        name="Unrealized P&L",
        marker_color="#FF6B6B"
    ))

    fig.update_layout(
        barmode="group",
        title="P&L by Symbol",
        yaxis_title="P&L ($)",
        template="plotly_dark"
    )

    return fig
