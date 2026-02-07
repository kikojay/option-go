"""月度快照页面 — 细分资产明细与即时汇率"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from ui import UI, plotly_layout
from services import SnapshotService
from config import ACCOUNT_CATEGORY_CN
from utils.currency import fetch_exchange_rates, to_rmb
import db


def render():
    UI.inject_css()
    UI.header("月度快照", "细分资产明细与即时汇率")

    usd_rmb = st.session_state.usd_rmb
    hkd_rmb = st.session_state.hkd_rmb

    # 1. 首屏指标
    s = SnapshotService.get_summary(usd_rmb, hkd_rmb)
    if s["accounts"]:
        c1, c2, c3 = st.columns(3)
        with c1:
            UI.card("当前总资产", s["total_rmb"], delta=s["delta_percent"],
                    subtext="最新账户余额")
        with c2:
            UI.card("美元账户", s["total_usd"] * usd_rmb,
                    subtext=f"${s['total_usd']:,.0f} x {usd_rmb:.2f}")
        with c3:
            UI.card("人民币账户", s["total_cny"],
                    subtext=f"¥{s['total_cny']:,.0f}")

    # 2. 快照生成表单
    _snapshot_forms(s, usd_rmb, hkd_rmb)

    # 3. 趋势图
    trend = SnapshotService.get_trend()
    if trend is not None:
        UI.sub_heading("资产趋势")
        fig = go.Figure(go.Scatter(
            x=trend["date_label"], y=trend["asset_wan"],
            mode="lines+markers",
            line=dict(color="#2B4C7E", width=3.5),
            marker=dict(size=12, symbol="circle",
                        line=dict(color="#F9F7F0", width=2)),
            hovertemplate="日期: %{x}<br>资产: ¥%{y:.2f}万<extra></extra>",
        ))
        fig.update_layout(**plotly_layout(
            height=350, margin=dict(l=20, r=20, t=20, b=20),
            hovermode="x unified"))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    # 4. 历史明细
    with UI.expander("查看历史快照明细", expanded=False):
        detail = SnapshotService.get_detail_rows(usd_rmb)
        if detail is not None:
            base_cols = [
                c for c in ["date", "total_usd", "total_rmb", "usd_cny", "note"]
                if c in detail.columns
            ]
            extra_cols = [c for c in detail.columns if c not in base_cols]
            col_map = {
                "date": "日期",
                "total_usd": "总资产(USD)",
                "total_rmb": "总资产(RMB)",
                "usd_cny": "USD/CNY",
                "note": "备注",
            }
            for col in extra_cols:
                if col in ACCOUNT_CATEGORY_CN:
                    col_map[col] = ACCOUNT_CATEGORY_CN[col]
            display = detail[base_cols + extra_cols].rename(columns=col_map)
            UI.table(display, max_height=500)
        else:
            st.caption("暂无快照")


def _snapshot_forms(summary, usd_rmb, hkd_rmb):
    """自动 / 手动生成快照。"""
    rates = fetch_exchange_rates()
    accts = summary["accounts"]
    c1, c2 = st.columns(2)

    with c1:
        with UI.expander("自动生成当前快照", expanded=False):
            if not accts:
                st.info("暂无账户数据"); return
            st.markdown(
                f'<div style="background:#f0f2f6;padding:16px;margin-bottom:10px">'
                f'<b>当前汇总：</b> USD: ${summary["total_usd"]:,.0f} '
                f'| CNY: ¥{summary["total_cny"]:,.0f}<br>'
                f'<b style="font-size:18px;color:#2B4C7E">'
                f'折合总资产: ¥{summary["total_rmb"]:,.0f}</b></div>',
                unsafe_allow_html=True)
            if st.button("确认生成快照", key="btn_auto_snap",
                         use_container_width=True):
                acct_data = [
                    {"name": a["name"], "category": a["category"],
                     "currency": a["currency"], "balance": a["balance"],
                     "balance_rmb": round(to_rmb(a["balance"], a["currency"], rates), 2)}
                    for a in accts]
                db.snapshots.create(
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    total_assets_usd=summary["total_usd"],
                    total_assets_rmb=summary["total_rmb"],
                    assets_data={"exchange_rates": {"USD_CNY": round(usd_rmb, 4),
                                                    "HKD_CNY": round(hkd_rmb, 4)},
                                 "accounts": acct_data},
                    note="自动生成")
                st.rerun()

    with c2:
        with UI.expander("手动输入快照", expanded=False):
            m_date = st.date_input("快照日期", value=datetime.now().date(),
                                   key="snap_date")
            m_note = st.text_input("备注", placeholder="例如：月末手工盘点",
                                   key="snap_note")
            cu, cr = st.columns(2)
            m_usd = cu.number_input("总资产 (USD)", value=0.0, step=100.0,
                                    key="snap_usd")
            m_rmb = cr.number_input("总资产 (RMB)", value=0.0, step=100.0,
                                    key="snap_rmb")
            if st.button("保存", key="btn_manual_snap",
                         use_container_width=True):
                if m_usd <= 0 and m_rmb <= 0:
                    st.error("请填写至少一个资产总额")
                else:
                    f_rmb = m_rmb if m_rmb > 0 else m_usd * usd_rmb
                    f_usd = m_usd if m_usd > 0 else m_rmb / usd_rmb
                    db.snapshots.create(
                        date_str=m_date.strftime("%Y-%m-%d"),
                        total_assets_usd=f_usd, total_assets_rmb=f_rmb,
                        assets_data={}, note=m_note or "手动输入")
                    st.rerun()
