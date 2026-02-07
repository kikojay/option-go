"""
数据库连接和操作模块 v2.0
支持个人资产管理 + 投资追踪
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "wealth_v2.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """初始化数据库"""
    schema_path = Path(__file__).parent / "schema.sql"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 读取并执行 schema
    with open(schema_path, 'r') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    # 初始化默认账户分类
    init_default_categories()
    
    conn.close()
    print(f"Database initialized: {DB_PATH}")


def init_default_categories():
    """初始化默认账户分类（去重：按 name 判断是否已存在）"""
    conn = get_connection()
    cursor = conn.cursor()

    # 先清除历史重复行：每个 name 只保留 id 最小的那条
    cursor.execute("""
        DELETE FROM accounts WHERE id NOT IN (
            SELECT MIN(id) FROM accounts GROUP BY name
        )
    """)

    # 确保 9 个默认分类存在
    asset_categories = [
        ('现金', 'cash', 'USD'),
        ('美股', 'stock', 'USD'),
        ('A股', 'stock', 'CNY'),
        ('港股', 'stock', 'HKD'),
        ('ETF', 'etf', 'USD'),
        ('加密货币', 'crypto', 'USD'),
        ('公积金', 'provident_fund', 'CNY'),
        ('应收账款', 'receivable', 'CNY'),
        ('其他', 'other', 'USD'),
    ]

    for name, cat, curr in asset_categories:
        existing = cursor.execute(
            "SELECT id FROM accounts WHERE name = ?", (name,)
        ).fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO accounts (name, type, category, currency) VALUES (?, 'asset', ?, ?)",
                (name, cat, curr),
            )

    conn.commit()
    conn.close()


# ==================== 汇率服务 ====================

def update_exchange_rate(date_str: str, currency: str, rate_usd: float, rate_rmb: float):
    """更新汇率"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO exchange_rates (date, currency, rate_to_usd, rate_to_rmb)
        VALUES (?, ?, ?, ?)
    """, (date_str, currency, rate_usd, rate_rmb))
    conn.commit()
    conn.close()


def get_exchange_rate(date_str: str, currency: str) -> Dict:
    """获取汇率"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rate_to_usd, rate_to_rmb FROM exchange_rates
        WHERE date = ? AND currency = ?
    """, (date_str, currency))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {'usd': row['rate_to_usd'], 'rmb': row['rate_to_rmb']}
    return {'usd': 1.0, 'rmb': 7.2}  # 默认值


def convert_to_rmb(amount: float, currency: str, date_str: str = None) -> float:
    """折算为 RMB"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    rates = get_exchange_rate(date_str, currency)
    
    if currency == 'CNY':
        return amount
    elif currency == 'HKD':
        return amount * rates['rmb'] / 7.8  # HKD 转 RMB
    else:  # USD
        return amount * rates['rmb']


# ==================== 账户管理 ====================

def get_all_accounts() -> List[Dict]:
    """获取所有账户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE is_active = 1 ORDER BY category, name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_account(name: str, category: str, currency: str = 'USD', balance: float = 0):
    """添加账户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (name, type, category, currency, balance)
        VALUES (?, 'asset', ?, ?, ?)
    """, (name, category, currency, balance))
    conn.commit()
    conn.close()


# ==================== 交易管理 ====================

def add_transaction(
    datetime_str: str,
    action: str,
    symbol: str = None,
    quantity: float = None,
    price: float = None,
    fees: float = 0,
    currency: str = 'USD',
    account_id: int = None,
    category: str = None,
    subcategory: str = None,
    target: str = None,
    note: str = None,
    strategy_id: int = None
) -> int:
    """添加交易记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions 
        (datetime, action, symbol, quantity, price, fees, currency, account_id, category, subcategory, target, note, strategy_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime_str, action, symbol, quantity, price, fees,
        currency, account_id, category, subcategory, target, note, strategy_id
    ))
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_transactions(
    symbol: str = None,
    start_date: str = None,
    end_date: str = None,
    category: str = None,
    limit: int = 100
) -> List[Dict]:
    """获取交易记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if start_date:
        query += " AND datetime >= ?"
        params.append(start_date)
    if end_date:
        query += " AND datetime <= ?"
        params.append(end_date)
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY datetime DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 快照管理 ====================

def create_snapshot(
    date_str: str,
    total_assets_usd: float,
    total_assets_rmb: float,
    assets_data: Dict,
    note: str = None
) -> int:
    """创建资产快照"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 取消之前的 latest 标记
    cursor.execute("UPDATE snapshots SET is_latest = 0 WHERE is_latest = 1")
    
    cursor.execute("""
        INSERT INTO snapshots (date, total_assets_usd, total_assets_rmb, assets_json, is_latest, note)
        VALUES (?, ?, ?, ?, 1, ?)
    """, (date_str, total_assets_usd, total_assets_rmb, json.dumps(assets_data), note))
    
    snap_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return snap_id


def get_latest_snapshot() -> Optional[Dict]:
    """获取最新快照"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snapshots WHERE is_latest = 1 ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = dict(row)
        data['assets_data'] = json.loads(data['assets_json']) if data.get('assets_json') else {}
        return data
    return None


def get_all_snapshots() -> List[Dict]:
    """获取所有快照"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snapshots ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        data = dict(row)
        data['assets_data'] = json.loads(data['assets_json']) if data.get('assets_json') else {}
        result.append(data)
    return result


# ==================== 策略管理 ====================

def create_strategy(name: str, type_: str, symbol: str = None, notes: str = None) -> int:
    """创建策略"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO strategies (name, type, symbol, status, start_date)
        VALUES (?, ?, ?, 'active', ?)
    """, (name, type_, symbol, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return cursor.lastrowid


def get_strategies(status: str = None) -> List[Dict]:
    """获取策略"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM strategies"
    if status:
        query += " WHERE status = ?"
        cursor.execute(query, (status,))
    else:
        cursor.execute(query)
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 年度汇总 ====================

def update_yearly_summary(
    year: int,
    pre_tax_income: float,
    social_insurance: float,
    income_tax: float,
    investment_income: float,
    note: str = None
):
    """更新年度汇总"""
    post_tax = pre_tax_income - social_insurance - income_tax + investment_income
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO yearly_summary 
        (year, pre_tax_income, social_insurance, income_tax, post_tax_income, investment_income, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (year, pre_tax_income, social_insurance, income_tax, post_tax, investment_income, note))
    conn.commit()
    conn.close()


def get_yearly_summary(year: int = None) -> List[Dict]:
    """获取年度汇总"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if year:
        cursor.execute("SELECT * FROM yearly_summary WHERE year = ?", (year,))
    else:
        cursor.execute("SELECT * FROM yearly_summary ORDER BY year DESC")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== 投资组合计算 ====================

def get_portfolio_summary(current_prices: Dict[str, float] = None) -> Dict:
    """获取投资组合汇总"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 按标的计算持仓
    cursor.execute("""
        SELECT 
            symbol,
            SUM(CASE WHEN action = 'BUY' THEN quantity ELSE 0 END) as shares_bought,
            SUM(CASE WHEN action = 'SELL' THEN quantity ELSE 0 END) as shares_sold,
            SUM(CASE WHEN action = 'BUY' THEN quantity * price ELSE 0 END) as total_cost,
            SUM(CASE WHEN action = 'SELL' THEN quantity * price ELSE 0 END) as total_sold,
            SUM(CASE WHEN action IN ('STO', 'SELL') THEN quantity * price ELSE 0 END) as option_premiums,
            AVG(CASE WHEN action = 'BUY' THEN price ELSE NULL END) as avg_cost
        FROM transactions
        WHERE category = '投资' AND symbol IS NOT NULL
        GROUP BY symbol
        HAVING (shares_bought - shares_sold) > 0
    """)
    
    holdings = []
    for row in cursor.fetchall():
        shares = row['shares_bought'] - row['shares_sold']
        current_price = current_prices.get(row['symbol']) if current_prices else None
        market_value = shares * current_price if current_price else 0
        cost_basis = row['total_cost'] - row['total_sold'] + row['option_premiums']
        unrealized = market_value - cost_basis
        
        holdings.append({
            'symbol': row['symbol'],
            'shares': shares,
            'avg_cost': row['avg_cost'] or 0,
            'cost_basis': cost_basis,
            'market_value': market_value,
            'unrealized_pnl': unrealized
        })
    
    conn.close()
    
    total_value = sum(h['market_value'] for h in holdings)
    total_cost = sum(h['cost_basis'] for h in holdings)
    
    return {
        'holdings': holdings,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_unrealized': total_value - total_cost
    }
