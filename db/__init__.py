"""
数据库访问层 — 统一导出

使用方式：
    from db import connection, transactions, accounts, exchange_rates, snapshots, yearly

    # 或者
    import db
    db.transactions.add(...)
    db.accounts.get_all()
"""
from db import connection
from db import transactions
from db import accounts
from db import exchange_rates
from db import snapshots
from db import yearly

__all__ = [
    "connection",
    "transactions",
    "accounts",
    "exchange_rates",
    "snapshots",
    "yearly",
]
