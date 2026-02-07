"""
dict → 旧 Transaction 转换器

将数据库行（dict）转为旧版 Transaction 模型，
供 PortfolioCalculator / WheelStrategyCalculator 使用。
"""
from services._legacy.models import Transaction, TransactionType


# action → (TransactionType, subtype) 映射
_TYPE_MAP = {
    "BUY":         (TransactionType.STOCK,  "buy"),
    "SELL":        (TransactionType.STOCK,  "sell"),
    "STO":         (TransactionType.OPTION, "sell_put"),
    "STO_CALL":    (TransactionType.OPTION, "sell_call"),
    "STC":         (TransactionType.OPTION, "buy_put"),
    "BTC":         (TransactionType.OPTION, "buy_put"),
    "BTO_CALL":    (TransactionType.OPTION, "buy_call"),
    "ASSIGNMENT":  (TransactionType.STOCK,  "assignment"),
    "CALLED_AWAY": (TransactionType.STOCK,  "called_away"),
}


def dict_to_transaction(d: dict) -> Transaction:
    """数据库行 → Transaction 模型

    金额规则：
    - 期权: amount = ±(price × qty × 100)
    - 股票: amount = ±(price × qty)
    - 正数 = 支出，负数 = 收入
    """
    action = d.get("action", "")

    if action in ("EXPENSE", "INCOME"):
        tx_type = (TransactionType.EXPENSE if action == "EXPENSE"
                   else TransactionType.INCOME)
        subtype = d.get("subcategory", "other")
    else:
        tx_type, subtype = _TYPE_MAP.get(
            action, (TransactionType.STOCK, None)
        )

    qty   = d.get("quantity", 1)
    price = d.get("price", 0)

    if tx_type == TransactionType.OPTION:
        sign = -1 if subtype in ("sell_put", "sell_call") else 1
        amount = sign * price * qty * 100
    elif tx_type == TransactionType.STOCK:
        amount = -(price * qty) if subtype in ("sell", "called_away") else price * qty
    else:
        amount = price * qty

    return Transaction(
        type=tx_type, subtype=subtype,
        date=d.get("datetime", "")[:10],
        amount=amount,
        symbol=d.get("symbol"),
        quantity=d.get("quantity"),
        price=d.get("price"),
        fees=d.get("fees", 0),
        category_id=d.get("category_id"),
        note=d.get("note"),
        strike_price=d.get("strike_price"),
        expiration_date=d.get("expiration_date"),
    )
