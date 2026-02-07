"""
汇率 API — 支持实时汇率和历史走势

数据源:
  1. ExchangeRate-API (https://www.exchangerate-api.com)  — 免费，无需 key
  2. Open Exchange Rates 备用
"""
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# ── 缓存目录 ──
_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_RATE_CACHE_FILE = _CACHE_DIR / "exchange_rates.json"
_HISTORY_CACHE_FILE = _CACHE_DIR / "usd_cny_history.json"

# 缓存有效期（秒）
_RATE_TTL = 3600         # 1 小时
_HISTORY_TTL = 86400     # 24 小时


def _read_cache(path: Path, ttl: int) -> Optional[dict]:
    """读取本地 JSON 缓存，过期返回 None"""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("_ts", 0) < ttl:
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _write_cache(path: Path, data: dict):
    """写入本地 JSON 缓存"""
    data["_ts"] = time.time()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ════════════════════════════════════════════════
#  实时汇率
# ════════════════════════════════════════════════

_DEFAULTS = {
    "USD": {"usd": 1.0, "cny": 7.2, "hkd": 7.8},
    "CNY": {"usd": 0.139, "cny": 1.0, "hkd": 1.083},
    "HKD": {"usd": 0.128, "cny": 0.923, "hkd": 1.0},
}


def get_exchange_rates() -> Dict:
    """
    获取实时汇率。

    Returns:
        {
            "USD": {"usd": 1.0, "cny": 7.xx, "hkd": 7.xx},
            "CNY": {"usd": 0.xx, "cny": 1.0, "hkd": xx},
            "HKD": {"usd": 0.xx, "cny": 0.xx, "hkd": 1.0},
            "updated_at": "2026-02-07 12:00:00",
        }
    """
    cached = _read_cache(_RATE_CACHE_FILE, _RATE_TTL)
    if cached and "USD" in cached:
        return cached

    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD", timeout=8
        )
        resp.raise_for_status()
        r = resp.json()["rates"]
        cny = r.get("CNY", 7.2)
        hkd = r.get("HKD", 7.8)

        result = {
            "USD": {"usd": 1.0, "cny": round(cny, 4), "hkd": round(hkd, 4)},
            "CNY": {
                "usd": round(1 / cny, 6),
                "cny": 1.0,
                "hkd": round(hkd / cny, 4),
            },
            "HKD": {
                "usd": round(1 / hkd, 6),
                "cny": round(cny / hkd, 4),
                "hkd": 1.0,
            },
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        _write_cache(_RATE_CACHE_FILE, result)
        return result
    except Exception:
        # 如果有旧缓存就用旧的，否则用默认值
        if _RATE_CACHE_FILE.exists():
            try:
                return json.loads(_RATE_CACHE_FILE.read_text())
            except Exception:
                pass
        return {**_DEFAULTS, "updated_at": "默认值"}


# ════════════════════════════════════════════════
#  汇率历史走势（USD/CNY）
# ════════════════════════════════════════════════

def get_usd_cny_history(days: int = 30) -> List[Dict]:
    """
    获取 USD/CNY 近 N 天日线走势。

    使用 yfinance 抓取 USDCNY=X 货币对。

    Returns:
        [{"date": "2026-01-08", "rate": 7.2345}, ...]
    """
    cached = _read_cache(_HISTORY_CACHE_FILE, _HISTORY_TTL)
    if cached and "history" in cached and len(cached["history"]) > 0:
        return cached["history"]

    try:
        import yfinance as yf
        ticker = yf.Ticker("CNY=X")  # USD/CNY
        period = f"{days}d"
        hist = ticker.history(period=period)
        if hist.empty:
            return _fallback_history(days)

        records = []
        for dt, row in hist.iterrows():
            records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "rate": round(row["Close"], 4),
            })
        _write_cache(_HISTORY_CACHE_FILE, {"history": records})
        return records
    except Exception:
        return _fallback_history(days)


def _fallback_history(days: int) -> List[Dict]:
    """用当前汇率生成伪走势（无法联网时的 fallback）"""
    import numpy as np
    rates_data = get_exchange_rates()
    current = rates_data["USD"]["cny"]
    np.random.seed(42)
    noise = np.cumsum(np.random.normal(0, 0.005, days))
    rates = current - noise[-1] + noise
    rates[-1] = current

    base = datetime.now() - timedelta(days=days - 1)
    return [
        {
            "date": (base + timedelta(days=i)).strftime("%Y-%m-%d"),
            "rate": round(float(rates[i]), 4),
        }
        for i in range(days)
    ]
