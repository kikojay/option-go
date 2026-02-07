"""
车轮策略图表数据 (mixin)

提供 heatmap / premium_bars / action_dist / option_detail_table
给 WheelService 使用。返回 DataFrame / Series，不含业务逻辑。
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from config import OPTION_ACTIONS, OPTION_ACTION_LABELS


class _WheelChartsMixin:
    """车轮策略图表方法，通过 mixin 注入 WheelService"""

    @staticmethod
    def heatmap(all_relevant: list, selected: str) -> Optional[pd.DataFrame]:
        """收益率热力图 pivot (月 x 操作)"""
        opts = [
            t for t in all_relevant
            if t["symbol"] == selected and t["action"] in OPTION_ACTIONS
        ]
        if not opts:
            return None
        heat = []
        for t in opts:
            month = t["datetime"][:7]
            prem = t["price"] * t["quantity"] * 100
            is_in = t["action"] in ("STO", "STO_CALL")
            heat.append({
                "month": month,
                "action": t["action"],
                "amount": prem if is_in else -prem,
            })
        hdf = pd.DataFrame(heat)
        pivot = hdf.pivot_table(
            index="action", columns="month", values="amount",
            aggfunc="sum", fill_value=0,
        )
        return pivot if not pivot.empty else None

    @staticmethod
    def premium_bars(all_relevant: list, selected: str) -> Optional[pd.Series]:
        """月度权利金柱图 Series"""
        df_opt = pd.DataFrame([
            t for t in all_relevant
            if t["symbol"] == selected and t["action"] in OPTION_ACTIONS
        ])
        if df_opt.empty:
            return None
        df_opt["date"] = pd.to_datetime(df_opt["datetime"])
        df_opt["premium_real"] = df_opt.apply(
            lambda r: r["price"] * r["quantity"] * 100
            * (1 if r["action"] in ("STO", "STO_CALL") else -1),
            axis=1,
        )
        return df_opt.groupby(
            df_opt["date"].dt.strftime("%Y-%m")
        )["premium_real"].sum()

    @staticmethod
    def action_dist(all_relevant: list, selected: str) -> Optional[pd.Series]:
        """操作分布 Series"""
        df_opt = pd.DataFrame([
            t for t in all_relevant
            if t["symbol"] == selected and t["action"] in OPTION_ACTIONS
        ])
        if df_opt.empty:
            return None
        return df_opt["action"].value_counts()

    @staticmethod
    def option_detail_table(
        all_relevant: list,
        selected: str,
        usd_rmb: float,
    ) -> Optional[pd.DataFrame]:
        """期权交易明细 DataFrame"""
        df_opt = pd.DataFrame([
            t for t in all_relevant
            if t["symbol"] == selected and t["action"] in OPTION_ACTIONS
        ])
        if df_opt.empty:
            return None
        d = df_opt[["datetime", "action", "quantity", "price", "fees"]].copy()
        d["date"] = pd.to_datetime(d["datetime"]).dt.strftime("%Y-%m-%d")
        d["premium_total"] = d["quantity"] * d["price"] * 100
        d["premium_rmb"] = d["premium_total"] * usd_rmb
        d["action_label"] = d["action"].map(OPTION_ACTION_LABELS).fillna(d["action"])
        return d[[
            "date",
            "action_label",
            "quantity",
            "price",
            "premium_total",
            "fees",
            "premium_rmb",
        ]]
