"""货币工具函数 — 汇率获取、金额转换"""
import streamlit as st
from typing import Dict

from api.exchange_rates import get_exchange_rates as _api_get_rates


@st.cache_data(ttl=3600)
def fetch_exchange_rates() -> Dict:
    """获取汇率（缓存 1 小时）。兼容旧接口 key 'rmb'"""
    raw = _api_get_rates()
    return {
        "USD": {"usd": 1.0, "rmb": raw["USD"]["cny"]},
        "CNY": {"usd": raw["CNY"]["usd"], "rmb": 1.0},
        "HKD": {"usd": raw["HKD"]["usd"], "rmb": raw["HKD"]["cny"]},
    }


def to_rmb(amount: float, currency: str, rates: Dict) -> float:
    """金额 → 人民币"""
    if currency == "CNY":
        return amount
    return amount * rates.get(currency, {}).get("rmb", 1.0)
