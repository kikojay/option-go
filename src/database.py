"""
数据库连接和操作模块
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from src.models import Transaction, Campaign, AccountCategory

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "wealth.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 账户分类表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,  -- 'asset' | 'liability' | 'income' | 'expense'
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 账户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES account_categories(id)
        )
    """)

    # 交易表（统一模型）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            subtype TEXT,
            date TIMESTAMP NOT NULL,
            symbol TEXT,
            account_id INTEGER,
            quantity INTEGER,
            price REAL,
            amount REAL NOT NULL,
            fees REAL DEFAULT 0,
            category_id INTEGER,
            note TEXT,
            strike_price REAL,
            expiration_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id),
            FOREIGN KEY (category_id) REFERENCES account_categories(id)
        )
    """)

    # 期权 Campaign 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            status TEXT DEFAULT 'active',  -- 'active' | 'closed' | 'paused'
            target_shares INTEGER DEFAULT 100,
            start_date DATE,
            end_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Campaign 关联的交易（用于追踪）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            transaction_id INTEGER NOT NULL,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    """)

    # 每日股价记录（用于计算浮动盈亏）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            price REAL NOT NULL,
            UNIQUE(symbol, date)
        )
    """)

    conn.commit()
    conn.close()

    # 初始化默认分类
    init_default_categories()


def init_default_categories():
    """初始化默认分类"""
    conn = get_connection()
    cursor = conn.cursor()

    # 资产分类
    categories = [
        # 资产
        ("Cash", "asset", None),
        ("Brokerage", "asset", None),
        ("Savings", "asset", None),
        ("AAPL", "asset", None),
        ("SLV", "asset", None),
        ("HOOD", "asset", None),
        # 负债
        ("Credit Card", "liability", None),
        ("Loan", "liability", None),
        # 收入
        ("Salary", "income", None),
        ("Investment Income", "income", None),
        ("Option Premium", "income", None),
        ("Dividend", "income", None),
        # 支出
        ("Food", "expense", None),
        ("Housing", "expense", None),
        ("Transportation", "expense", None),
        ("Entertainment", "expense", None),
        ("Utilities", "expense", None),
        ("Healthcare", "expense", None),
        ("Shopping", "expense", None),
        ("Other", "expense", None),
    ]

    for name, type_, parent in categories:
        try:
            cursor.execute(
                "INSERT INTO account_categories (name, type, parent_id) VALUES (?, ?, ?)",
                (name, type_, parent)
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


def add_transaction(tx: Transaction) -> int:
    """添加交易记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions 
        (type, subtype, date, symbol, account_id, quantity, price, amount, fees, category_id, note, strike_price, expiration_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tx.type, tx.subtype, tx.date, tx.symbol, tx.account_id,
        tx.quantity, tx.price, tx.amount, tx.fees, tx.category_id, tx.note,
        tx.strike_price, tx.expiration_date
    ))
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_transactions(filters: dict = None) -> list:
    """获取交易记录"""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT t.*, ac.name as category_name, a.name as account_name
        FROM transactions t
        LEFT JOIN account_categories ac ON t.category_id = ac.id
        LEFT JOIN accounts a ON t.account_id = a.id
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get("symbol"):
            query += " AND t.symbol = ?"
            params.append(filters["symbol"])
        if filters.get("type"):
            query += " AND t.type = ?"
            params.append(filters["type"])
        if filters.get("start_date"):
            query += " AND t.date >= ?"
            params.append(filters["start_date"])
        if filters.get("end_date"):
            query += " AND t.date <= ?"
            params.append(filters["end_date"])

    query += " ORDER BY t.date DESC LIMIT ?"
    params.append(filters.get("limit", 100) if filters else 100)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def create_campaign(symbol: str, target_shares: int = 100, start_date: str = None) -> int:
    """创建 Campaign"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO campaigns (symbol, target_shares, start_date, status)
        VALUES (?, ?, ?, 'active')
    """, (symbol, target_shares, start_date or datetime.now().date()))
    campaign_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return campaign_id


def get_campaigns() -> list:
    """获取所有 Campaigns"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_categories_by_type(category_type: str) -> list:
    """按类型获取分类"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM account_categories WHERE type = ? ORDER BY name",
        (category_type,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_accounts() -> list:
    """获取所有账户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, ac.name as category_name
        FROM accounts a
        LEFT JOIN account_categories ac ON a.category_id = ac.id
        WHERE a.is_active = 1
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_daily_price(symbol: str, date: str, price: float):
    """更新每日股价"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO daily_prices (symbol, date, price)
        VALUES (?, ?, ?)
    """, (symbol, date, price))
    conn.commit()
    conn.close()


def get_latest_price(symbol: str) -> float:
    """获取最新股价"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT price FROM daily_prices
        WHERE symbol = ?
        ORDER BY date DESC LIMIT 1
    """, (symbol,))
    row = cursor.fetchone()
    conn.close()
    return row["price"] if row else None


def get_portfolio_summary() -> dict:
    """获取投资组合汇总"""
    conn = get_connection()
    cursor = conn.cursor()

    # 各股票持仓
    cursor.execute("""
        SELECT 
            symbol,
            SUM(CASE WHEN subtype IN ('buy', 'assignment') THEN quantity ELSE 0 END) as shares_bought,
            SUM(CASE WHEN subtype IN ('sell', 'called_away') THEN quantity ELSE 0 END) as shares_sold,
            SUM(CASE WHEN subtype IN ('buy', 'assignment') THEN amount ELSE 0 END) as total_cost,
            SUM(CASE WHEN subtype IN ('sell', 'called_away') THEN amount ELSE 0 END) as total_sold,
            SUM(CASE WHEN subtype = 'sell_put' THEN amount ELSE 0 END) as put_premiums,
            SUM(CASE WHEN subtype = 'sell_call' THEN amount ELSE 0 END) as call_premiums
        FROM transactions
        WHERE type = 'stock'
        GROUP BY symbol
        HAVING (shares_bought - shares_sold) > 0
    """)

    holdings = {}
    for row in cursor.fetchall():
        symbol = row["symbol"]
        shares = row["shares_bought"] - row["shares_sold"]
        latest_price = get_latest_price(symbol)
        market_value = shares * latest_price if latest_price else 0
        unrealized_pnl = market_value - (row["total_cost"] - row["total_sold"] - row["put_premiums"] - row["call_premiums"])

        holdings[symbol] = {
            "symbol": symbol,
            "shares": shares,
            "avg_cost": (row["total_cost"] - row["total_sold"] - row["put_premiums"] - row["call_premiums"]) / shares if shares else 0,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl
        }

    # 总资产
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN ac.type = 'asset' THEN a.balance ELSE 0 END) as total_assets,
            SUM(CASE WHEN ac.type = 'liability' THEN a.balance ELSE 0 END) as total_liabilities
        FROM accounts a
        LEFT JOIN account_categories ac ON a.category_id = ac.id
    """)

    assets = cursor.fetchone()

    # 计算总盈亏
    total_realized = 0
    total_unrealized = 0
    for h in holdings.values():
        total_unrealized += h.get("unrealized_pnl", 0)
    # Realized P&L 需要从交易记录计算
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    cursor2.execute("""
        SELECT
            SUM(CASE WHEN subtype IN ('sell_put', 'sell_call') THEN -amount ELSE 0 END) as option_pnl,
            SUM(CASE WHEN subtype IN ('sell', 'called_away') THEN -amount ELSE 0 END) as stock_sell_pnl,
            SUM(CASE WHEN subtype IN ('buy', 'assignment') THEN amount ELSE 0 END) as stock_buy_pnl,
            SUM(fees) as total_fees
        FROM transactions
        WHERE type IN ('stock', 'option')
    """)
    pnl_row = cursor2.fetchone()
    conn2.close()

    total_realized = (pnl_row["option_pnl"] or 0) + (pnl_row["stock_sell_pnl"] or 0) - (pnl_row["stock_buy_pnl"] or 0) - (pnl_row["total_fees"] or 0)

    conn.close()

    return {
        "holdings": holdings,
        "total_assets": assets["total_assets"] or 0,
        "total_liabilities": assets["total_liabilities"] or 0,
        "net_worth": (assets["total_assets"] or 0) - (assets["total_liabilities"] or 0),
        "total_realized_pnl": total_realized,
        "total_unrealized_pnl": total_unrealized,
        "total_pnl": total_realized + total_unrealized
    }
