"""页面：月度快照 Snapshots（修复版）"""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_all_accounts, create_snapshot, get_all_snapshots
from .config import COLORS, CATEGORY_CN
from .helpers import fetch_exchange_rates, to_rmb, plotly_layout


def page_snapshots():
    # 1. 顶部标题与样式注入
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman&display=swap');
            html, body, [class*="st-"] {
                font-family: 'Times New Roman', serif;
            }
            .big-font { font-size:18px !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        "<h1 style='margin-bottom:4px; font-family:Georgia, serif;'>月度快照</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>Monthly Snapshots · 细分资产明细与即时汇率</p>"
        "<hr style='border:none;border-top:2px solid #2D2D2D;margin-top:0;margin-bottom:20px'>",
        unsafe_allow_html=True,
    )

    # 获取基础数据
    accounts = get_all_accounts()
    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # 2. 自动生成与手动输入（合并到 Expander 中）
    col_snap1, col_snap2 = st.columns(2)
    
    with col_snap1:
        with st.expander("自动生成当前快照", expanded=False):
            if accounts:
                total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
                total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
                total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
                total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

                # 使用 Markdown 渲染确保没有源代码泄露
                st.markdown(f"""
                    <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:10px">
                        <b>当前汇总：</b><br>
                        USD: ${total_usd:,.0f} | CNY: ¥{total_cny:,.0f}<br>
                        <span style="font-size:18px; color:#2B4C7E;">折合总资产: ¥{total_rmb:,.0f}</span>
                    </div>
                """, unsafe_allow_html=True)

                if st.button("确认生成快照", key="btn_auto_snap", use_container_width=True):
                    create_snapshot(
                        date_str=datetime.now().strftime("%Y-%m-%d"),
                        total_assets_usd=total_usd,
                        total_assets_rmb=total_rmb,
                        assets_data={
                            "exchange_rates": {"USD_CNY": round(usd_rmb, 4), "HKD_CNY": round(hkd_rmb, 4)},
                            "accounts": [{"name": a["name"], "category": a["category"], "currency": a["currency"], 
                                         "balance": a["balance"], "balance_rmb": round(to_rmb(a["balance"], a["currency"], rates), 2)} 
                                        for a in accounts]
                        },
                        note="自动生成",
                    )
                    st.rerun()

    with col_snap2:
        with st.expander("手动输入快照", expanded=False):
            m_date = st.date_input("快照日期", value=datetime.now().date(), key="snap_date")
            m_note = st.text_input("备注", placeholder="例如：月末手工盘点", key="snap_note")

            c_usd, c_rmb = st.columns(2)
            m_usd = c_usd.number_input("总资产 (USD)", value=0.0, step=100.0, key="snap_usd")
            m_rmb = c_rmb.number_input("总资产 (RMB)", value=0.0, step=100.0, key="snap_rmb")

            if st.button("保存", key="btn_manual_snap", use_container_width=True):
                if m_usd <= 0 and m_rmb <= 0:
                    st.error("请填写至少一个资产总额")
                else:
                    final_rmb = m_rmb if m_rmb > 0 else m_usd * usd_rmb
                    final_usd = m_usd if m_usd > 0 else m_rmb / usd_rmb
                    create_snapshot(
                        date_str=m_date.strftime("%Y-%m-%d"),
                        total_assets_usd=final_usd,
                        total_assets_rmb=final_rmb,
                        assets_data={},
                        note=m_note or "手动输入",
                    )
                    st.rerun()

    # 3. 趋势图表（万单位，中文坐标）
    snapshots = get_all_snapshots()
    if snapshots:
        df = pd.DataFrame(snapshots)
        df["date_parsed"] = pd.to_datetime(df["date"])
        df = df.sort_values("date_parsed", ascending=True)
        
        # 转换单位为万
        df["资产(万)"] = df["total_assets_rmb"] / 10000
        df["日期中文"] = df["date_parsed"].dt.strftime("%Y年%m月%d日")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["日期中文"],
            y=df["资产(万)"],
            mode="lines+markers",
            line=dict(color="#2B4C7E", width=3),
            marker=dict(size=10, symbol="circle"),
            hovertemplate="日期: %{x}<br>资产: ¥%{y:.2f}万<extra></extra>"
        ))
        
        fig.update_layout(**plotly_layout(
            height=350,
            xaxis_title="快照日期",
            yaxis_title="资产价值 (万元)",
            margin=dict(l=20, r=20, t=20, b=20)
        ))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # 4. 快照列表（核心修复：倒序、细分明细、双币对比）
    st.markdown('<hr style="border:none;border-top:1px solid #2D2D2D;margin:1rem 0">',
                unsafe_allow_html=True)
    st.markdown(
        "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px'>历史明细 (日期倒序)</h3>",
        unsafe_allow_html=True,
    )
    
    if snapshots:
        display_df = df.sort_values("date_parsed", ascending=False).copy()
        
        rows = []
        for _, row in display_df.iterrows():
            data = row.get("assets_data", {})
            if isinstance(data, str): data = json.loads(data) if data else {}
            
            res = {
                "日期": row["date_parsed"].strftime("%Y-%m-%d"),
                "总资产(USD)": row["total_assets_usd"],
                "总资产(RMB)": row["total_assets_rmb"],
                "USD/CNY": data.get("exchange_rates", {}).get("USD_CNY", usd_rmb),
                "备注": row.get("note", "")
            }
            # 提取细分资产
            accs = data.get("accounts", [])
            for a in accs:
                cat_name = CATEGORY_CN.get(a.get('category', ''), a.get('category', ''))
                res[cat_name] = res.get(cat_name, 0) + a.get('balance_rmb', 0)
            rows.append(res)

        final_df = pd.DataFrame(rows).fillna(0)
        
        # 使用 column_config 强制千分位和字体效果
        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "日期": st.column_config.TextColumn("快照日期"),
                "总资产(USD)": st.column_config.NumberColumn("总计 (USD)", format="$%,.2f"),
                "总资产(RMB)": st.column_config.NumberColumn("总计 (RMB)", format="¥%,.0f"),
                "USD/CNY": st.column_config.NumberColumn("汇率", format="%.4f"),
            }
        )
    else:
        st.caption("暂无快照")
