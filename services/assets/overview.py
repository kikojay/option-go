"""
总览服务 — 资产概览 + 趋势

数据来源：accounts 表 + snapshots 表
不涉及 transactions，只看账户余额和快照历史。

预留接口：
- fx_mode 参数（§2.10.2）用于汇率归因抵扣
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import db
from config import ACCOUNT_CATEGORY_CN
from config.theme import COLORS

# 资产类别配色
_PALETTE: Dict[str, str] = {
    "现金": "#2B4C7E", "股票": "#5B8C5A", "ETF": "#D4A017",
    "加密货币": "#C0392B", "公积金": "#6C3483",
    "应收账款": "#48B4A0", "其他": "#D4783A",
}
_FALLBACK = ["#7E8C6E", "#937B6A", "#5C7A99", "#A67D5D"]


class OverviewService:
    """
    总览服务

    提供资产概览指标和趋势数据。
    所有方法为 @staticmethod，接收汇率参数（触发缓存失效）。
    """

    @staticmethod
    @st.cache_data(ttl=600)
    def get_metrics(
        usd_rmb: float,
        hkd_rmb: float,
        fx_mode: str = "current",
    ) -> Dict[str, Any]:
        """
        计算总资产概览

        Args:
            usd_rmb: 美元兑人民币汇率
            hkd_rmb: 港币兑人民币汇率
            fx_mode: 汇率视角 ("current" | "fixed" | "entry")，预留

        Returns:
            {total_rmb, total_usd, total_cny, total_hkd,
             usd_rmb, hkd_rmb, delta_percent,
             cat_breakdown: [{cat, color, value}],
             accounts}
        """
        accounts = db.accounts.get_all()
        snapshots = db.snapshots.get_all()

        # 按币种汇总
        total_usd = sum(a["balance"] for a in accounts if a["currency"] == "USD")
        total_cny = sum(a["balance"] for a in accounts if a["currency"] == "CNY")
        total_hkd = sum(a["balance"] for a in accounts if a["currency"] == "HKD")
        total_rmb = total_usd * usd_rmb + total_cny + total_hkd * hkd_rmb

        # 按类别汇总（人民币）
        def _to_rmb(amount: float, currency: str) -> float:
            if currency == "CNY":
                return amount
            if currency == "USD":
                return amount * usd_rmb
            if currency == "HKD":
                return amount * hkd_rmb
            return amount

        cats: Dict[str, float] = {}
        for a in accounts:
            cn = ACCOUNT_CATEGORY_CN.get(a.get("category", ""), a.get("category", ""))
            cats[cn] = cats.get(cn, 0) + _to_rmb(a["balance"], a["currency"])
        cats = dict(sorted(cats.items(), key=lambda x: -abs(x[1])))

        breakdown = []
        for idx, (cat, val) in enumerate(cats.items()):
            color = _PALETTE.get(cat, _FALLBACK[idx % len(_FALLBACK)])
            breakdown.append({"cat": cat, "color": color, "value": val})

        # 变化率：与最近快照比
        delta = None
        if snapshots and len(snapshots) >= 2:
            s = sorted(snapshots, key=lambda x: x["date"], reverse=True)
            prev = s[1].get("total_assets_rmb", 0)
            if prev > 0:
                delta = ((s[0].get("total_assets_rmb", 0) - prev) / prev) * 100

        return {
            "total_rmb": total_rmb,
            "total_usd": total_usd,
            "total_cny": total_cny,
            "total_hkd": total_hkd,
            "usd_rmb":   usd_rmb,
            "hkd_rmb":   hkd_rmb,
            "delta_percent": delta,
            "cat_breakdown": breakdown,
            "accounts":  accounts,
        }

    @staticmethod
    @st.cache_data(ttl=600)
    def get_trend() -> Optional[pd.DataFrame]:
        """
        快照走势 DataFrame（万元）

        Returns:
            DataFrame(date, asset_wan) 或 None
        """
        snapshots = db.snapshots.get_all()
        if not snapshots:
            return None
        df = pd.DataFrame(snapshots)
        df["date_parsed"] = pd.to_datetime(df["date"])
        df = df.sort_values("date_parsed")
        df["date"] = df["date_parsed"].dt.strftime("%Y-%m-%d")
        df["asset_wan"] = df["total_assets_rmb"] / 10000
        return df[["date", "asset_wan"]]
