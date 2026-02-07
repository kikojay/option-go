"""
交易分类与操作常量 — Single Source of Truth

本文件是整个系统中关于「交易分类」「操作类型」的唯一定义处。
任何新增/修改操作类型都只改这一个文件。
"""
from enum import Enum
from typing import FrozenSet, List, Dict

# ═══════════════════════════════════════════════════════
#  Streamlit 页面配置
# ═══════════════════════════════════════════════════════

PAGE_CONFIG: Dict = dict(
    page_title="财富追踪器",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
#  交易分类 — 一级枚举（互斥，不可交叉）
# ═══════════════════════════════════════════════════════

class TransactionCategory(str, Enum):
    """
    交易记录的一级分类（互斥，不可交叉）

    - INCOME:     收入（工资、奖金、副业）
    - EXPENSE:    支出（生活开销）
    - INVESTMENT: 投资本金进出（入金/出金）
    - TRADING:    交易操作（买卖/期权/分红）
    """
    INCOME     = "INCOME"
    EXPENSE    = "EXPENSE"
    INVESTMENT = "INVESTMENT"
    TRADING    = "TRADING"


# ═══════════════════════════════════════════════════════
#  二级分类（subcategory）
# ═══════════════════════════════════════════════════════

# 收入子分类
INCOME_SUBCATEGORIES: List[str] = [
    "工资", "奖金", "副业", "退税", "礼金", "其他收入",
]

# 支出子分类
EXPENSE_SUBCATEGORIES: List[str] = [
    "餐饮", "房租", "交通", "日用", "外食", "在家吃饭",
    "订阅", "家庭", "医疗", "娱乐", "教育", "其他支出",
]

# 投资子分类（本金流动）
INVESTMENT_SUBCATEGORIES: List[str] = [
    "入金", "出金",
]

# 交易子分类（买卖操作产生的记录）
TRADING_SUBCATEGORIES: List[str] = [
    "股票", "期权", "分红", "ETF",
]

# 分类 → 子分类映射（用于表单校验）
CATEGORY_SUBCATEGORIES: Dict[TransactionCategory, List[str]] = {
    TransactionCategory.INCOME:     INCOME_SUBCATEGORIES,
    TransactionCategory.EXPENSE:    EXPENSE_SUBCATEGORIES,
    TransactionCategory.INVESTMENT: INVESTMENT_SUBCATEGORIES,
    TransactionCategory.TRADING:    TRADING_SUBCATEGORIES,
}


# ═══════════════════════════════════════════════════════
#  操作类型（action）按域分组
# ═══════════════════════════════════════════════════════

# 记账操作（域 2: 日常记账）
ACCOUNTING_ACTIONS: FrozenSet[str] = frozenset({
    "INCOME", "EXPENSE",
})

# 投资本金操作（域 3: 投资 — 不产生盈亏）
CAPITAL_ACTIONS: FrozenSet[str] = frozenset({
    "DEPOSIT", "WITHDRAW",
})

# 股票交易操作（域 3: 投资 — 影响持仓）
STOCK_ACTIONS: FrozenSet[str] = frozenset({
    "BUY", "SELL", "ASSIGNMENT", "CALLED_AWAY",
})

# 期权交易操作（域 3: 投资 — 影响期权持仓）
OPTION_ACTIONS: FrozenSet[str] = frozenset({
    "STO", "STO_CALL", "STC", "BTC", "BTO_CALL",
})

# 收益类操作（域 3: 投资 — 产生现金流但不影响持仓）
YIELD_ACTIONS: FrozenSet[str] = frozenset({
    "DIVIDEND",
})

# 所有投资相关操作（域 3 的完整集合）
INVESTMENT_ACTIONS: FrozenSet[str] = (
    CAPITAL_ACTIONS | STOCK_ACTIONS | OPTION_ACTIONS | YIELD_ACTIONS
)

# 所有合法 action 值（用于入库校验）
ALL_ACTIONS: FrozenSet[str] = ACCOUNTING_ACTIONS | INVESTMENT_ACTIONS


# ═══════════════════════════════════════════════════════
#  action → category 自动推断
# ═══════════════════════════════════════════════════════

def infer_category(action: str) -> TransactionCategory:
    """
    根据 action 自动推断一级 category（入库时调用）

    规则：
    - INCOME        → INCOME
    - EXPENSE       → EXPENSE
    - DEPOSIT/WITHDRAW → INVESTMENT
    - BUY/SELL/STO/... → TRADING

    Raises:
        ValueError: 当 action 不在 ALL_ACTIONS 中时抛出
    """
    if action == "INCOME":
        return TransactionCategory.INCOME
    if action == "EXPENSE":
        return TransactionCategory.EXPENSE
    if action in CAPITAL_ACTIONS:
        return TransactionCategory.INVESTMENT
    if action in (STOCK_ACTIONS | OPTION_ACTIONS | YIELD_ACTIONS):
        return TransactionCategory.TRADING
    raise ValueError(f"未知操作类型: {action}，合法值: {ALL_ACTIONS}")
