"""
快照服务 — 资产快照管理

数据来源：accounts 表 + snapshots 表
提供快照汇总、趋势、明细三个核心方法。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import db


class SnapshotService:
    """
    快照服务

    提供快照相关的全部计算和数据准备。
    """

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_summary(
        usd_rmb: float,
        hkd_rmb: float,
    ) -> Dict[str, Any]:
        """
        当前账户汇总 + 与上期快照的变化率

        Args:
            usd_rmb: 美元兑人民币汇率
            hkd_rmb: 港币兑人民币汇率

        Returns:
            {total_usd, total_cny, total_hkd, total_rmb,
             delta_percent, accounts}
        """
        accounts = db.accounts.get_all()
        snapshots = db.snapshots.get_all()

        total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
        total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
        total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
        total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

        delta = None
        if snapshots:
            latest_total = sorted(
                snapshots, key=lambda x: x["date"], reverse=True
            )[0].get("total_assets_rmb", 0)
            if latest_total > 0:
                delta = ((total_rmb - latest_total) / latest_total) * 100

        return {
            "total_usd": total_usd,
            "total_cny": total_cny,
            "total_hkd": total_hkd,
            "total_rmb": total_rmb,
            "delta_percent": delta,
            "accounts": accounts,
        }

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_trend() -> Optional[pd.DataFrame]:
        """
        资产走势（万元），含中文日期

        Returns:
            DataFrame(date_label, asset_wan) 或 None
        """
        snapshots = db.snapshots.get_all()
        if not snapshots:
            return None
        df = pd.DataFrame(snapshots)
        df["date_parsed"] = pd.to_datetime(df["date"])
        df = df.sort_values("date_parsed")
        df["date_label"] = df["date_parsed"].dt.strftime("%Y年%m月%d日")
        df["asset_wan"] = df["total_assets_rmb"] / 10000
        return df[["date_label", "asset_wan"]]

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_detail_rows(usd_rmb: float) -> Optional[pd.DataFrame]:
        """
        历史快照明细 DataFrame，含细分资产列

        Args:
            usd_rmb: 美元兑人民币汇率（用作 fallback）

        Returns:
            DataFrame 或 None
        """
        snapshots = db.snapshots.get_all()
        if not snapshots:
            return None
        df = pd.DataFrame(snapshots)
        df["date_parsed"] = pd.to_datetime(df["date"])
        display = df.sort_values("date_parsed", ascending=False)

        rows = []
        for _, row in display.iterrows():
            data = row.get("assets_data", {})
            if isinstance(data, str):
                data = json.loads(data) if data else {}

            res = {
                "date": row["date_parsed"].strftime("%Y-%m-%d"),
                "total_usd": row.get("total_assets_usd", 0),
                "total_rmb": row.get("total_assets_rmb", 0),
                "usd_cny": data.get("exchange_rates", {}).get("USD_CNY", usd_rmb),
                "note": row.get("note", ""),
            }
            for a in data.get("accounts", []):
                cat_key = a.get("category", "")
                res[cat_key] = res.get(cat_key, 0) + a.get("balance_rmb", 0)
            rows.append(res)
        return pd.DataFrame(rows).fillna(0)
