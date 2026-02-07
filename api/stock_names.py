"""
股票中文名 API — 自动从 yfinance 获取英文名，结合本地映射提供中文名

策略:
  1. 优先查本地 JSON 映射文件（可手动补充/修正）
  2. 本地没有 → 从 yfinance 获取 shortName
  3. 常见美股有内置中文翻译表
  4. 提供 refresh 接口批量更新
"""
import json
from pathlib import Path
from typing import Dict, Optional

import yfinance as yf

# ── 文件路径 ──
_DATA_DIR = Path(__file__).parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_NAMES_FILE = _DATA_DIR / "stock_names.json"

# ── 内置常用美股中文翻译（作为默认值种子，可被 JSON 文件覆盖） ──
_BUILTIN_CN = {
    "AAPL": "苹果", "MSFT": "微软", "GOOGL": "谷歌", "GOOG": "谷歌",
    "AMZN": "亚马逊", "TSLA": "特斯拉", "NVDA": "英伟达", "META": "Meta",
    "AMD": "超威半导体", "INTC": "英特尔", "AVGO": "博通",
    "VOO": "标普500ETF", "QQQ": "纳指100ETF", "SPY": "标普500ETF",
    "IWM": "罗素2000ETF", "DIA": "道指ETF",
    "GLD": "黄金ETF", "SLV": "白银ETF", "IAU": "黄金ETF(iShares)",
    "PLTR": "Palantir", "COIN": "Coinbase", "SOFI": "SoFi",
    "BABA": "阿里巴巴", "JD": "京东", "PDD": "拼多多", "NIO": "蔚来",
    "XPEV": "小鹏", "LI": "理想", "BILI": "哔哩哔哩", "BIDU": "百度",
    "NTES": "网易", "TME": "腾讯音乐", "ZH": "知乎", "FUTU": "富途",
    "MARA": "Marathon", "RIOT": "Riot",
    "JPM": "摩根大通", "BAC": "美国银行", "GS": "高盛", "MS": "摩根士丹利",
    "V": "Visa", "MA": "万事达", "PYPL": "PayPal",
    "DIS": "迪士尼", "NFLX": "奈飞", "SPOT": "Spotify",
    "CRM": "Salesforce", "ORCL": "甲骨文", "IBM": "IBM",
    "BA": "波音", "CAT": "卡特彼勒", "MMM": "3M",
    "KO": "可口可乐", "PEP": "百事", "MCD": "麦当劳",
    "JNJ": "强生", "PFE": "辉瑞", "UNH": "联合健康",
    "WMT": "沃尔玛", "COST": "好市多", "TGT": "Target",
    "XOM": "埃克森美孚", "CVX": "雪佛龙",
    "BRK-B": "伯克希尔B",
}


def _load_names_file() -> Dict[str, Dict]:
    """加载本地名称映射文件"""
    if _NAMES_FILE.exists():
        try:
            return json.loads(_NAMES_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_names_file(data: Dict[str, Dict]):
    """保存名称映射到本地 JSON"""
    _NAMES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _fetch_name_from_yfinance(symbol: str) -> Optional[Dict]:
    """从 yfinance 获取标的名称信息"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        short_name = info.get("shortName", "")
        long_name = info.get("longName", "")
        if short_name or long_name:
            return {
                "en": short_name or long_name,
                "cn": _BUILTIN_CN.get(symbol.upper(), ""),
                "source": "yfinance",
            }
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════
#  公开接口
# ════════════════════════════════════════════════

def get_stock_name(symbol: str) -> str:
    """
    获取股票的显示名称（优先中文，fallback 英文名）。

    Returns:
        "苹果" 或 "Apple Inc." 或原始代码
    """
    sym = symbol.upper()
    names = _load_names_file()

    # 1) 已有本地缓存
    if sym in names:
        entry = names[sym]
        cn = entry.get("cn", "")
        if cn:
            return cn
        return entry.get("en", sym)

    # 2) 检查内置翻译
    if sym in _BUILTIN_CN:
        return _BUILTIN_CN[sym]

    # 3) 从 yfinance 拉取并缓存
    fetched = _fetch_name_from_yfinance(sym)
    if fetched:
        names[sym] = fetched
        _save_names_file(names)
        return fetched["cn"] or fetched["en"] or sym

    return sym


def get_stock_names(symbols: list) -> Dict[str, str]:
    """
    批量获取股票名称。

    Returns:
        {"AAPL": "苹果", "SLV": "白银ETF", ...}
    """
    return {sym: get_stock_name(sym) for sym in symbols}


def refresh_stock_names(symbols: list) -> Dict[str, Dict]:
    """
    强制刷新指定标的名称（重新从 yfinance 拉取）。

    Returns:
        完整的 {symbol: {en, cn, source}} 映射
    """
    names = _load_names_file()
    for sym in symbols:
        sym = sym.upper()
        fetched = _fetch_name_from_yfinance(sym)
        if fetched:
            # 保留用户手动设置的中文名
            existing_cn = names.get(sym, {}).get("cn", "")
            if existing_cn and not fetched["cn"]:
                fetched["cn"] = existing_cn
            elif not fetched["cn"]:
                fetched["cn"] = _BUILTIN_CN.get(sym, "")
            names[sym] = fetched
    _save_names_file(names)
    return names


def get_stock_label(symbol: str) -> str:
    """
    返回 "AAPL 苹果" 格式的标签。

    比直接调 get_stock_name 多带上代码前缀。
    """
    name = get_stock_name(symbol)
    if name and name != symbol:
        return f"{symbol} {name}"
    return symbol
