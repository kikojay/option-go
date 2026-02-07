"""
投资组合 — 持仓明细 Tab (mixin)

提供 build_holdings_rows / calc_holdings_footer 给 PortfolioService 使用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from api.stock_names import get_stock_name
from ._helpers import estimate_dividends as _estimate_dividends


class _HoldingsMixin:
    """持仓明细相关方法（Tab 2），通过 mixin 注入 PortfolioService"""

    @staticmethod
    def build_holdings_rows(data: dict) -> List[Dict[str, Any]]:
        """
        持仓明细行列表，可直接转 DataFrame

        Returns:
            list of dicts，每个 dict 是一行持仓
        """
        holdings = data["holdings"]
        live_prices = data["live_prices"]
        usd_rmb = data["usd_rmb"]

        total_cost = sum(
            h.get("cost_basis", 0) for h in holdings.values()
            if int(h.get("current_shares", 0)) > 0
        )

        rows = []
        for sym, h in holdings.items():
            shares = int(h.get("current_shares", 0))
            if shares <= 0:
                continue

            cost = h.get("cost_basis", 0)
            adj = h.get("adjusted_cost", 0)
            prem = h.get("total_premiums", 0)
            pnl = h.get("unrealized_pnl", 0)
            pct = (cost / total_cost * 100) if total_cost > 0 else 0

            pi = live_prices.get(sym, {})
            cprice = pi.get("price", 0)
            chg = pi.get("change_pct", 0)
            mv_usd = cprice * shares if cprice else cost
            mv_rmb = mv_usd * usd_rmb

            # 分红估算
            adiv, mdiv = _estimate_dividends(sym, shares)

            rows.append({
                "symbol": sym,
                "company": get_stock_name(sym),
                "shares": shares,
                "price_usd": cprice,
                "change_pct": chg,
                "cost_usd": cost,
                "cost_rmb": round(cost * usd_rmb),
                "value_usd": round(mv_usd),
                "value_rmb": round(mv_rmb),
                "adjusted_cost_per_share": adj,
                "premiums": -prem,
                "pnl_usd": pnl,
                "pnl_rmb": round(pnl * usd_rmb),
                "monthly_dividend_usd": round(mdiv, 2),
                "yearly_dividend_usd": round(adiv, 2),
                "weight": pct / 100,
            })
        return rows

    @staticmethod
    def calc_holdings_footer(
        rows: List[dict],
        usd_rmb: float,
    ) -> List[Tuple[str, str]]:
        """
        持仓合计底部数据

        Returns:
            [(label, formatted_value), ...]
        """
        if not rows:
            return []
        t = lambda k: sum(r[k] for r in rows)
        tc = t("cost_usd")
        return [
            ("成本合计", f"${tc:,.0f} / ¥{tc * usd_rmb:,.0f}"),
            ("市值合计", f"${t('value_usd'):,.0f} / ¥{t('value_rmb'):,.0f}"),
            ("盈亏合计", f"${t('pnl_usd'):+,.0f}"),
            ("累计权利金", f"${t('premiums'):,.0f}"),
            ("预估年收息", f"${t('yearly_dividend_usd'):,.2f}"),
            ("预估月分红", f"${t('monthly_dividend_usd'):,.2f}"),
        ]
