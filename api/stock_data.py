"""
股票价格 API — 基于 yfinance

功能:
  - 实时/最近收盘价
  - 日线历史数据
  - 批量获取多标的价格
"""
import json
import time
import yfinance as yf
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


# ── 缓存 ──
_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_PRICE_CACHE_FILE = _CACHE_DIR / "stock_prices.json"
_PRICE_TTL = 300  # 5 分钟


def _load_price_cache() -> dict:
    if _PRICE_CACHE_FILE.exists():
        try:
            return json.loads(_PRICE_CACHE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_price_cache(data: dict):
    _PRICE_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ════════════════════════════════════════════════
#  单个标的实时价格
# ════════════════════════════════════════════════

def get_current_price(symbol: str) -> Optional[Dict]:
    """
    获取单个标的的实时/最近价格。

    Returns:
        {
            "symbol": "AAPL",
            "price": 278.12,
            "previous_close": 275.91,
            "change": 2.21,
            "change_pct": 0.80,
            "currency": "USD",
            "name": "Apple Inc.",
            "updated_at": "2026-02-07 12:00:00",
        }
        或 None（获取失败）
    """
    cache = _load_price_cache()
    key = symbol.upper()
    if key in cache:
        entry = cache[key]
        if time.time() - entry.get("_ts", 0) < _PRICE_TTL:
            return entry

    try:
        ticker = yf.Ticker(key)
        info = ticker.info
        price = info.get("currentPrice") or info.get("previousClose") or info.get("regularMarketPrice")
        prev = info.get("previousClose", price)
        if price is None:
            return None

        change = round(price - prev, 2)
        change_pct = round((change / prev) * 100, 2) if prev else 0

        result = {
            "symbol": key,
            "price": price,
            "previous_close": prev,
            "change": change,
            "change_pct": change_pct,
            "currency": info.get("currency", "USD"),
            "name": info.get("shortName", key),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_ts": time.time(),
        }

        cache[key] = result
        _save_price_cache(cache)
        return result
    except Exception:
        return cache.get(key)  # 返回旧缓存


# ════════════════════════════════════════════════
#  批量获取价格
# ════════════════════════════════════════════════

def get_batch_prices(symbols: List[str]) -> Dict[str, Dict]:
    """
    批量获取多标的最新价格。

    Returns:
        {"AAPL": {...}, "SLV": {...}, ...}
    """
    result = {}
    # 先从缓存拿未过期的
    cache = _load_price_cache()
    need_fetch = []
    for sym in symbols:
        key = sym.upper()
        if key in cache and time.time() - cache[key].get("_ts", 0) < _PRICE_TTL:
            result[key] = cache[key]
        else:
            need_fetch.append(key)

    if not need_fetch:
        return result

    # 用 yfinance.download 批量拉最新一根 bar
    try:
        tickers = yf.Tickers(" ".join(need_fetch))
        for sym in need_fetch:
            try:
                t = tickers.tickers[sym]
                info = t.info
                price = info.get("currentPrice") or info.get("previousClose") or info.get("regularMarketPrice")
                prev = info.get("previousClose", price)
                if price is None:
                    continue
                change = round(price - prev, 2)
                change_pct = round((change / prev) * 100, 2) if prev else 0
                entry = {
                    "symbol": sym,
                    "price": price,
                    "previous_close": prev,
                    "change": change,
                    "change_pct": change_pct,
                    "currency": info.get("currency", "USD"),
                    "name": info.get("shortName", sym),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "_ts": time.time(),
                }
                result[sym] = entry
                cache[sym] = entry
            except Exception:
                continue
        _save_price_cache(cache)
    except Exception:
        pass

    return result


# ════════════════════════════════════════════════
#  历史价格（日线）
# ════════════════════════════════════════════════

def get_price_history(
    symbol: str,
    period: str = "3mo",
    interval: str = "1d",
) -> List[Dict]:
    """
    获取标的历史日线数据。

    Args:
        symbol: 股票代码，如 "AAPL"
        period: 时间段 "1mo", "3mo", "6mo", "1y", "2y", "5y"
        interval: 间隔 "1d", "1wk", "1mo"

    Returns:
        [{"date": "2026-01-06", "open": 150.0, "high": ..., "low": ...,
          "close": 152.0, "volume": 123456}, ...]
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return []

        records = []
        for dt, row in hist.iterrows():
            records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception:
        return []
