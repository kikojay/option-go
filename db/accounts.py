"""
账户 CRUD

纯数据访问，不含业务逻辑。
"""
from typing import Optional, List, Dict, Any

from db.connection import get_connection


# 默认账户分类（种子数据）
_DEFAULT_ACCOUNTS = [
    ("现金",     "cash",           "USD"),
    ("美股",     "stock",          "USD"),
    ("A股",      "stock",          "CNY"),
    ("港股",     "stock",          "HKD"),
    ("ETF",      "etf",            "USD"),
    ("加密货币", "crypto",          "USD"),
    ("公积金",   "provident_fund",  "CNY"),
    ("应收账款", "receivable",      "CNY"),
    ("其他",     "other",           "USD"),
]


def init_defaults():
    """
    初始化默认账户（幂等：已存在则跳过）

    去重规则：按 name 判断唯一性，先清除历史重复行。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 清除历史重复行：每个 name 只保留 id 最小的那条
    cursor.execute("""
        DELETE FROM accounts WHERE id NOT IN (
            SELECT MIN(id) FROM accounts GROUP BY name
        )
    """)

    for name, cat, curr in _DEFAULT_ACCOUNTS:
        existing = cursor.execute(
            "SELECT id FROM accounts WHERE name = ?", (name,)
        ).fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO accounts (name, type, category, currency) "
                "VALUES (?, 'asset', ?, ?)",
                (name, cat, curr),
            )

    conn.commit()
    conn.close()


def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
    """获取所有账户（默认只返回活跃账户）"""
    conn = get_connection()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE is_active = 1 ORDER BY category, name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM accounts ORDER BY category, name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取账户"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add(
    name: str,
    category: str,
    *,
    account_type: str = "asset",
    currency: str = "USD",
    balance: float = 0,
) -> int:
    """
    添加账户

    Returns:
        新账户的 ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO accounts (name, type, category, currency, balance) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, account_type, category, currency, balance),
    )
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return account_id


def update_balance(account_id: int, new_balance: float) -> bool:
    """更新账户余额"""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE accounts SET balance = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = ?",
        (new_balance, account_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def deactivate(account_id: int) -> bool:
    """停用账户（软删除）"""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE accounts SET is_active = 0, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = ?",
        (account_id,),
    )
    conn.commit()
    deactivated = cursor.rowcount > 0
    conn.close()
    return deactivated
