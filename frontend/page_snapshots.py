"""页面：月度快照 Snapshots（含细分资产明细 + 即时汇率）"""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.database_v2 import get_all_accounts, create_snapshot, get_all_snapshots

from .config import COLORS, CATEGORY_CN
from .helpers import fetch_exchange_rates, to_rmb, plotly_layout


def page_snapshots():
    st.markdown(
        "<h1 style='margin-bottom:4px'>月度快照</h1>"
        "<p style='color:#6B6B6B;font-size:14px;margin-top:0'>Monthly Snapshots · 含细分资产明细与即时汇率</p>",
        unsafe_allow_html=True,
    )

    accounts = get_all_accounts()
    rates = fetch_exchange_rates()
    usd_rmb = rates["USD"]["rmb"]
    hkd_rmb = rates["HKD"]["rmb"]

    # ══════════════════════════════════════════════════════
    #  自动生成快照
    # ══════════════════════════════════════════════════════

    with st.expander("📸 从当前账户自动生成快照", expanded=False):
        if accounts:
            total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
            total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
            total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
            total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

            st.info(
                f"当前账户汇总 — USD: ${total_usd:,.0f} · "
                f"CNY: ¥{total_cny:,.0f} · HKD: HK${total_hkd:,.0f} · "
                f"折合 ¥{total_rmb:,.0f}"
            )

            preview_rows = []
            for a in accounts:
                rmb_val = to_rmb(a["balance"], a["currency"], rates)
                preview_rows.append({
                    "账户": a["name"],
                    "类别": CATEGORY_CN.get(a["category"], a["category"]),
                    "币种": a["currency"],
                    "余额": a["balance"],
                    "折合(RMB)": rmb_val,
                })
            pdf = pd.DataFrame(preview_rows)
            st.dataframe(pdf, use_container_width=True, hide_index=True,
                         column_config={
                             "余额": st.column_config.NumberColumn("余额", format="%,.2f"),
                             "折合(RMB)": st.column_config.NumberColumn("折合(RMB)", format="¥%,.0f"),
                         })

            if st.button("📸 生成快照", key="btn_auto_snap"):
                create_snapshot(
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    total_assets_usd=total_usd,
                    total_assets_rmb=total_rmb,
                    assets_data={
                        "exchange_rates": {
                            "USD_CNY": round(usd_rmb, 4),
                            "HKD_CNY": round(hkd_rmb, 4),
                        },
                        "accounts": [
                            {
                                "name": a["name"],
                                "category": a["category"],
                                "currency": a["currency"],
                                "balance": a["balance"],
                                "balance_rmb": round(to_rmb(a["balance"], a["currency"], rates), 2),
                            }
                            for a in accounts
                        ],
                    },
                    note="自动生成",
                )
                st.success("快照已创建！")
                st.rerun()
        else:
            st.warning("暂无账户数据，无法自动生成快照。")

    # ── 手动输入 ──
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

        if st.button("保存手动快照", key="btn_manual_snap"):
            if m_usd <= 0 and m_rmb <= 0:
                st.error("请填写至少一个资产总额")
            else:
                final_rmb = m_rmb if m_rmb > 0 else m_usd * usd_rmb
                final_usd = m_usd if m_usd > 0 else m_rmb / usd_rmb
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
                st.success("手动快照已保存！")
                st.rerun()

    # ══════════════════════════════════════════════════════
    #  快照数据展示
    # ══════════════════════════════════════════════════════

    snapshots = get_all_snapshots()
    if not snapshots:
        st.caption("暂无快照")
        return

    df = pd.DataFrame(snapshots)
    df["date_parsed"] = pd.to_datetime(df["date"])
    df = df.sort_values("date_parsed", ascending=True)

    # ── 总资产走势图 ──
    df["日期"] = df["date_parsed"].dt.strftime("%Y-%m-%d")
    df["资产(万)"] = df["total_assets_rmb"] / 10000

    fig = go.Figure(go.Scatter(
        x=df["日期"],
        y=df["资产(万)"],
        mode="lines+markers",
        name="总资产",
        line=dict(color="#2B4C7E", width=3.5, shape="spline"),
        marker=dict(size=8, color="#2B4C7E",
                    line=dict(color="#F9F7F0", width=2)),
        hovertemplate="%{x}<br>¥%{y:.2f} 万元<extra></extra>",
    ))
    fig.update_layout(**plotly_layout(
        height=340,
        xaxis_title="日期",
        yaxis_title="总资产（万元）",
        hovermode="x unified",
        margin=dict(l=55, r=15, t=15, b=40),
    ))
    fig.update_yaxes(ticksuffix=" 万")
    st.plotly_chart(fig, use_container_width=True, key="snap_trend")

    st.markdown('<hr style="border:none;border-top:1px solid #2D2D2D;margin:1rem 0">',
                unsafe_allow_html=True)

    # ── 快照列表（倒序）──
    st.markdown(
        "<h3 style='color:#2D2D2D;font-weight:700;font-size:1rem;"
        "font-family:Georgia,serif;border-bottom:1px solid #2D2D2D;"
        "padding-bottom:4px'>快照列表</h3>",
        unsafe_allow_html=True,
    )

    display = df.sort_values("date_parsed", ascending=False).copy()
    display["日期"] = display["date_parsed"].dt.strftime("%Y年%m月%d日")

    # 解析每一行的 assets_data 以展示细分明细
    detail_rows = []
    for _, row in display.iterrows():
        base = {
            "日期": row["日期"],
            "总资产(USD)": row["total_assets_usd"],
            "总资产(RMB)": row["total_assets_rmb"],
            "备注": row.get("note", ""),
        }

        assets_data = row.get("assets_data")
        if isinstance(assets_data, str):
            try:
                assets_data = json.loads(assets_data)
            except (json.JSONDecodeError, TypeError):
                assets_data = None

        if assets_data and isinstance(assets_data, dict):
            ex_rates = assets_data.get("exchange_rates", {})
            base["USD/CNY"] = ex_rates.get("USD_CNY", "")
            base["HKD/CNY"] = ex_rates.get("HKD_CNY", "")

            accs = assets_data.get("accounts", [])
            # 按类别汇总
            cat_sums = {}
            for a in accs:
                cn_cat = CATEGORY_CN.get(a.get("category", ""), a.get("category", ""))
                cat_sums[cn_cat] = cat_sums.get(cn_cat, 0) + a.get("balance_rmb", 0)
            for cat, val in cat_sums.items():
                base[cat] = val
        else:
            base["USD/CNY"] = ""
            base["HKD/CNY"] = ""

        detail_rows.append(base)

    detail_df = pd.DataFrame(detail_rows).fillna("")

    # 固定列顺序 + 动态资产类别列
    fixed_cols = ["日期", "总资产(USD)", "总资产(RMB)", "USD/CNY", "HKD/CNY"]
    cat_cols = [c for c in detail_df.columns if c not in fixed_cols + ["备注"]]
    col_order = fixed_cols + sorted(cat_cols) + ["备注"]
    col_order = [c for c in col_order if c in detail_df.columns]
    detail_df = detail_df[col_order]

    # 构建 column_config
    col_cfg = {
        "总资产(USD)": st.column_config.NumberColumn("总资产(USD)", format="$%,.0f"),
        "总资产(RMB)": st.column_config.NumberColumn("总资产(RMB)", format="¥%,.0f"),
    }
    for cc in cat_cols:
        if cc and detail_df[cc].dtype in ("float64", "int64", "float32"):
            col_cfg[cc] = st.column_config.NumberColumn(cc, format="¥%,.0f")

    st.dataframe(detail_df, use_container_width=True, hide_index=True,
                 column_config=col_cfg)
