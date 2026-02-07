"""
交易记录 CRUD

纯数据访问，不含业务逻辑。
所有写入操作自动通过 infer_category() 推断 category。
"""
from typing import Optional, List, Dict, Any

from db.connection import get_connection
from config.constants import infer_category, TransactionCategory


def add(
    datetime_str: str,
    action: str,
    *,
    symbol: Optional[str] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    fees: float = 0,
    currency: str = "USD",
    account_id: Optional[int] = None,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
) -> int:
    """
    添加交易记录

    category 根据 action 自动推断（由 infer_category 决定），
    调用方无需手动传入。

    Args:
        datetime_str: ISO 时间戳 (YYYY-MM-DD HH:MM:SS)
        action:       操作类型（必须属于 ALL_ACTIONS）
        symbol:       股票代码（投资操作必填，记账操作可选）
        quantity:     数量
        price:        单价
        fees:         手续费
        currency:     货币 (USD/CNY/HKD)
        account_id:   关联账户 ID
        subcategory:  二级分类
        note:         备注

    Returns:
        新记录的 ID
    """
    category = infer_category(action).value

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions
        (datetime, action, symbol, quantity, price, fees, currency,
         account_id, category, subcategory, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime_str, action, symbol, quantity, price, fees,
        currency, account_id, category, subcategory, note,
    ))
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_by_id(tx_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取单条交易记录"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ?", (tx_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def query(
    *,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_in: Optional[List[TransactionCategory]] = None,
    action_in: Optional[set] = None,
    account_id: Optional[int] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    灵活查询交易记录

    Args:
        symbol:      按股票代码过滤
        start_date:  起始日期 (>=)
        end_date:    截止日期 (<=)
        category_in: 按一级分类过滤（列表，OR 关系）
        action_in:   按操作类型过滤（集合，OR 关系）
        account_id:  按账户 ID 过滤
        limit:       返回条数上限

    Returns:
        交易记录列表（按时间倒序）
    """
    clauses = ["1=1"]
    params: list = []

    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol)
    if start_date:
        clauses.append("datetime >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("datetime <= ?")
        params.append(end_date)
    if category_in:
        placeholders = ",".join("?" for _ in category_in)
        clauses.append(f"category IN ({placeholders})")
        params.extend(c.value if isinstance(c, TransactionCategory) else c for c in category_in)
    if action_in:
        placeholders = ",".join("?" for _ in action_in)
        clauses.append(f"action IN ({placeholders})")
        params.extend(action_in)
    if account_id:
        clauses.append("account_id = ?")
        params.append(account_id)

    where = " AND ".join(clauses)
    sql = f"SELECT * FROM transactions WHERE {where} ORDER BY datetime DESC LIMIT ?"
    params.append(limit)

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete(tx_id: int) -> bool:
    """删除交易记录，返回是否成功"""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update(tx_id: int, **fields) -> bool:
    """
    更新交易记录的指定字段

    如果更新了 action，category 会自动重新推断。

    Args:
        tx_id:   记录 ID
        **fields: 要更新的字段名=值

    Returns:
        是否更新成功
    """
    if not fields:
        return False

    # 如果更新了 action，重新推断 category
    if "action" in fields:
        fields["category"] = infer_category(fields["action"]).value

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tx_id]

    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE transactions SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated
