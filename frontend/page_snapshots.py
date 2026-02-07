"""页面：月度快照 Snapshots（支持自动生成 + 手动输入）"""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_all_accounts, create_snapshot, get_all_snapshots

from .config import COLORS
from .helpers import fetch_exchange_rates, to_rmb, plotly_layout


def page_snapshots():
    st.title("📅 月度快照 Snapshots")

    accounts = get_all_accounts()
    rates = fetch_exchange_rates()

    # ── 自动从账户生成快照 ──
    with st.expander("📸 从当前账户自动生成快照", expanded=False):
        if accounts:
            total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
            total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
            total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
            total_rmb = (
                total_usd * rates["USD"]["rmb"]
                + total_cny
                + total_hkd * rates["HKD"]["rmb"]
            )
            st.info(
                f"当前账户汇总 &mdash; USD: ${total_usd:,.0f} · "
                f"CNY: ¥{total_cny:,.0f} · HKD: HK${total_hkd:,.0f} · "
                f"折合 ¥{total_rmb:,.0f}"
            )
            if st.button("📸 生成快照", key="btn_auto_snap"):
                create_snapshot(
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    total_assets_usd=total_usd,
                    total_assets_rmb=total_rmb,
                    assets_data={
                        "accounts": [
                            {
                                "name": a["name"],
                                "balance": a["balance"],
                                "currency": a["currency"],
                            }
                            for a in accounts
                        ]
                    },
                    note="自动生成",
                )
                st.success("✅ 快照已创建！")
                st.rerun()
        else:
            st.warning("暂无账户数据，无法自动生成快照。")

    # ── 手动输入快照 ──
    with st.expander("✏️ 手动输入快照", expanded=False):
        c1, c2 = st.columns(2)
        m_date = c1.date_input("快照日期", value=datetime.now().date(), key="snap_date")
        m_note = c2.text_input("备注", placeholder="例如：月末手工盘点", key="snap_note")

        c3, c4 = st.columns(2)
        m_usd = c3.number_input("总资产 (USD)", value=0.0, step=100.0, key="snap_usd")
        m_rmb = c4.number_input("总资产 (RMB)", value=0.0, step=100.0, key="snap_rmb")

        m_detail = st.text_area(
            "资产明细 JSON（可选）",
            placeholder='{"accounts": [{"name": "xxx", "balance": 1000, "currency": "USD"}]}',
            height=80,
            key="snap_json",
        )

        if st.button("💾 保存手动快照", key="btn_manual_snap"):
            if m_usd <= 0 and m_rmb <= 0:
                st.error("请填写至少一个资产总额")
            else:
                # 如果只填了 USD 则自动折算 RMB
                final_rmb = m_rmb if m_rmb > 0 else m_usd * rates["USD"]["rmb"]
                final_usd = m_usd if m_usd > 0 else m_rmb / rates["USD"]["rmb"]
                assets = {}
                if m_detail.strip():
                    try:
                        assets = json.loads(m_detail)
                    except json.JSONDecodeError:
                        st.warning("JSON 格式不正确，已忽略明细")

                create_snapshot(
                    date_str=m_date.strftime("%Y-%m-%d"),
                    total_assets_usd=final_usd,
                    total_assets_rmb=final_rmb,
                    assets_data=assets,
                    note=m_note or "手动输入",
                )
                st.success("✅ 手动快照已保存！")
                st.rerun()

    # ── 快照数据展示 ──
    snapshots = get_all_snapshots()
    if not snapshots:
        st.caption("暂无快照")
        return

    df = pd.DataFrame(snapshots)

    fig = go.Figure(go.Scatter(
        x=df["date"],
        y=df["total_assets_rmb"],
        mode="lines+markers",
        name="总资产 (RMB)",
        line=dict(color=COLORS["primary"], width=2),
        fill="tozeroy",
        fillcolor="rgba(26,115,232,0.08)",
    ))
    fig.update_layout(
        **plotly_layout(xaxis_title="日期", yaxis_title="资产 (RMB)", hovermode="x unified")
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["date", "total_assets_usd", "total_assets_rmb", "note"]],
        use_container_width=True,
        hide_index=True,
    )
