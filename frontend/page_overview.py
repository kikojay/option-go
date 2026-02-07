"""页面：总览 Overview — 复古金融报告风格"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Tuple

from src.database_v2 import get_all_accounts, get_all_snapshots

from .config import COLORS, CATEGORY_CN
from .helpers import fetch_exchange_rates, to_rmb, plotly_layout


# ── 资产类别配色（复古：深蓝/薄荷绿/橄榄/橙黄/红）──
_PALETTE = {
    "现金":     "#2B4C7E",   # deep navy blue
    "股票":     "#5B8C5A",   # olive green
    "ETF":      "#D4A017",   # gold yellow
    "加密货币":  "#C0392B",   # brick red
    "公积金":   "#6C3483",   # plum purple
    "应收账款":  "#48B4A0",   # mint teal
    "其他":     "#D4783A",   # burnt orange
}
_FALLBACK_COLORS = ["#7E8C6E", "#937B6A", "#5C7A99", "#A67D5D"]


def _cat_color(cat: str, idx: int) -> str:
    if cat in _PALETTE:
        return _PALETTE[cat]
    return _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)]


# ── 页面级 CSS（复古金融报告） ──
_PAGE_CSS = """
<style>
/* 资产表格 — 复古，只有水平线 */
.nw-table { width:100%; border-collapse:collapse; font-size:16px;
            font-family:Georgia, 'Times New Roman', serif; }
.nw-table th { text-align:left; padding:14px 14px; background:#98C379; color:#1A1A1A;
               font-weight:700; border-bottom:2px solid #2D2D2D; font-size:15px;
               text-transform:uppercase; letter-spacing:0.5px;
               border-left:none; border-right:none; }
.nw-table td { padding:12px 14px; border-bottom:1px solid #C8C3B5; color:#2D2D2D;
               border-left:none; border-right:none; }
.nw-table .amt { font-family:'Times New Roman', Georgia, serif; font-weight:700; }
.nw-table tr:hover td { background:#F0EDE3; }
.nw-table .total-row td { font-weight:700; font-size:17px; border-top:2px solid #2D2D2D;
                           border-bottom:2px solid #2D2D2D;
                           background:#F0EDE3; color:#1A1A1A;
                           border-left:none; border-right:none; }
.nw-table .color-dot { display:inline-block; width:11px; height:11px; border-radius:50%;
                        margin-right:8px; vertical-align:middle; }
/* 底栏总净值 */
.nw-footer { text-align:center; padding:24px 0 12px; }
.nw-footer .label { color:#6B6B6B; font-size:15px; font-weight:400;
                     font-family:Georgia, serif; text-transform:uppercase;
                     letter-spacing:1.5px; margin-bottom:6px; }
.nw-footer .value { color:#2D2D2D; font-size:2.6rem; font-weight:700;
                     font-family:'Times New Roman', Georgia, serif;
                     letter-spacing:-0.5px; }
</style>
"""


def _build_asset_table(cat_data: List[Tuple[str, str, float]]) -> str:
    """生成 HTML 资产表格。Total 行 = 所有可见行之和"""
    rows_html = ""
    table_total = 0.0
    for cat, color, value in cat_data:
        table_total += value
        rows_html += (
            '<tr>'
            f'<td><span class="color-dot" style="background:{color}"></span>{cat}</td>'
            f'<td class="amt" style="text-align:right">¥{value:,.0f}</td>'
            '</tr>'
        )
    return (
        '<table class="nw-table">'
        '<thead><tr><th>资产类别</th><th style="text-align:right">价值 (RMB)</th></tr></thead>'
        '<tbody>'
        f'{rows_html}'
        '<tr class="total-row">'
        '<td>Total Assets</td>'
        f'<td class="amt" style="text-align:right">¥{table_total:,.0f}</td>'
        '</tr>'
        '</tbody></table>'
    )


def page_overview():
    # ── 页面级样式 ──
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

    # ── Header（紧凑标题）──
    st.markdown(
        "<h1 style='margin-bottom:4px'>Net Worth: Overview</h1>",
        unsafe_allow_html=True,
    )

    # ── 数据准备 ──
    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]
    accounts = get_all_accounts()

    total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
    total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
    total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
    total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

    snapshots = get_all_snapshots()

    # ── 按类别汇总（含负值，不过滤）──
    cat_assets: Dict[str, float] = {}
    for a in accounts:
        cn_cat = CATEGORY_CN.get(a["category"], a["category"])
        cat_assets[cn_cat] = cat_assets.get(cn_cat, 0) + to_rmb(
            a["balance"], a["currency"], rates
        )
    # 按金额降序（保留所有，包括负值）
    cat_assets = dict(sorted(cat_assets.items(), key=lambda x: -abs(x[1])))

    # 为每个类别分配颜色
    cat_colors: List[Tuple[str, str, float]] = []
    for idx, (cat, val) in enumerate(cat_assets.items()):
        cat_colors.append((cat, _cat_color(cat, idx), val))

    # ══════════════════════════════════════════════════════
    #  3-column layout:  Table | Pie | Trend
    # ══════════════════════════════════════════════════════

    col_table, col_pie, col_trend = st.columns([1, 1, 1.2])

    # ── 左栏: 资产列表 ──
    with col_table:
        if cat_colors:
            html_table = _build_asset_table(cat_colors)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.info("暂无账户数据")

    # ── 中栏: 资产配置饼图（实心，白色文字）──
    with col_pie:
        if cat_colors:
            # 饼图只显示正值
            pie_data = [(c, clr, v) for c, clr, v in cat_colors if v > 0]
            if pie_data:
                labels = [c[0] for c in pie_data]
                values = [c[2] for c in pie_data]
                colors = [c[1] for c in pie_data]
                fig = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    hole=0,  # 实心饼图
                    marker=dict(
                        colors=colors,
                        line=dict(color="#F9F7F0", width=2),
                    ),
                    textinfo="label+percent",
                    textfont=dict(size=14, family="'Times New Roman', Georgia, serif",
                                  color="#FFFFFF"),
                    insidetextorientation="radial",
                    hovertemplate="%{label}<br>¥%{value:,.0f}<br>%{percent}<extra></extra>",
                    sort=False,
                ))
                fig.update_layout(**plotly_layout(
                    height=420,
                    margin=dict(l=5, r=5, t=10, b=10),
                    showlegend=False,
                ))
                st.plotly_chart(fig, use_container_width=True, key="overview_pie")

    # ── 右栏: 总资产增长曲线 ──
    with col_trend:
        st.markdown(
            "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
            "font-family:Georgia,serif;margin:0 0 6px;"
            "border-bottom:1px solid #2D2D2D;padding-bottom:5px'>总资产增长曲线</h3>",
            unsafe_allow_html=True,
        )
        if snapshots:
            sdf = pd.DataFrame(snapshots)
            sdf["date_parsed"] = pd.to_datetime(sdf["date"])
            sdf["日期"] = sdf["date_parsed"].dt.strftime("%Y-%m-%d")
            sdf["资产(万)"] = sdf["total_assets_rmb"] / 10000

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sdf["日期"],
                y=sdf["资产(万)"],
                mode="lines+markers",
                line=dict(color="#2B4C7E", width=3.5, shape="spline"),
                marker=dict(size=9, color="#2B4C7E", symbol="circle",
                            line=dict(color="#F9F7F0", width=2)),
                hovertemplate="%{x}<br><b>¥%{y:.2f} 万</b><extra></extra>",
            ))
            fig.update_layout(**plotly_layout(
                height=400,
                margin=dict(l=55, r=15, t=10, b=40),
                hovermode="x unified",
                showlegend=False,
            ))
            fig.update_yaxes(ticksuffix=" 万")
            st.plotly_chart(fig, use_container_width=True, key="overview_trend")
        else:
            st.caption("暂无快照数据，去「月度快照」页面创建")

    # ══════════════════════════════════════════════════════
    #  底栏: Total Net Worth（上方黑线分割）
    # ══════════════════════════════════════════════════════

    st.markdown('<hr style="border:none;border-top:2px solid #2D2D2D;margin:1.5rem 0 0">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="nw-footer">'
        f'<div class="label">Total Net Worth</div>'
        f'<div class="value">¥{total_rmb:,.0f}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
