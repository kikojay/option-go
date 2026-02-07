"""
数据库连接管理 + Schema 初始化

唯一的数据库连接入口。启用 WAL 模式支持 VPS 多设备并发访问。
"""
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

# 数据库路径（默认 prod + shadow）
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "wealth.db"
SHADOW_DB_PATH = Path(__file__).parent.parent / "data" / "wealth_test.db"


def get_db_path() -> Path:
    """获取数据库路径（支持 prod/shadow 与自定义路径）。"""
    env_path = os.getenv("WEALTH_DB_PATH")
    if env_path:
        return Path(env_path)
    role = os.getenv("WEALTH_DB_ROLE", "prod").lower()
    return SHADOW_DB_PATH if role == "shadow" else DEFAULT_DB_PATH


# 兼容旧引用（注意：此值在 import 时固定）
DB_PATH = get_db_path()

# ═══════════════════════════════════════════════════════
#  Schema — 5 个核心表（含 CHECK 约束 + 索引）
# ═══════════════════════════════════════════════════════

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('asset', 'liability')),
    category    TEXT,
    currency    TEXT DEFAULT 'USD',
    balance     REAL DEFAULT 0,
    is_active   INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime    TIMESTAMP NOT NULL,
    symbol      TEXT,
    action      TEXT NOT NULL CHECK(
        action IN ('INCOME','EXPENSE','DEPOSIT','WITHDRAW',
                   'BUY','SELL','STO','STO_CALL','STC','BTC','BTO_CALL',
                   'ASSIGNMENT','CALLED_AWAY','DIVIDEND')
    ),
    quantity    REAL,
    price       REAL,
    fees        REAL DEFAULT 0,
    currency    TEXT DEFAULT 'USD',
    account_id  INTEGER REFERENCES accounts(id),
    category    TEXT NOT NULL CHECK(
        category IN ('INCOME','EXPENSE','INVESTMENT','TRADING')
    ),
    subcategory TEXT,
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_action   ON transactions(action);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_symbol   ON transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_tx_datetime ON transactions(datetime);

CREATE TABLE IF NOT EXISTS exchange_rates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        DATE NOT NULL,
    currency    TEXT NOT NULL,
    rate_to_usd REAL,
    rate_to_rmb REAL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, currency)
);
CREATE INDEX IF NOT EXISTS idx_er_date ON exchange_rates(date);

CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             DATE NOT NULL,
    total_assets_usd REAL,
    total_assets_rmb REAL,
    assets_json      TEXT,
    note             TEXT
);

CREATE TABLE IF NOT EXISTS yearly_summary (
    year              INTEGER NOT NULL UNIQUE,
    pre_tax_income    REAL DEFAULT 0,
    social_insurance  REAL DEFAULT 0,
    income_tax        REAL DEFAULT 0,
    post_tax_income   REAL DEFAULT 0,
    investment_income REAL DEFAULT 0,
    note              TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    """
    获取数据库连接（单次使用）

    启用：
    - WAL 模式：支持并发读 + 单写，VPS 多设备安全
    - foreign_keys：外键约束生效
    - Row factory：查询结果可按列名访问

    注意：此函数返回的连接不缓存，每次调用创建新连接。
    在 Streamlit 环境中，应通过 @st.cache_resource 包装后使用。
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """
    初始化数据库 Schema + 默认账户

    幂等操作：所有 CREATE 语句带 IF NOT EXISTS，重复调用安全。
    应在 app.py 启动时调用一次。
    """
    conn = get_connection()
    conn.executescript(_SCHEMA)
    conn.close()

    # 初始化默认账户（幂等）
    from db.accounts import init_defaults
    init_defaults()


def sync_shadow_from_prod(
    prod_path: Optional[Path] = None,
    shadow_path: Optional[Path] = None,
    *,
    overwrite: bool = True,
) -> Path:
    """将 prod 数据一键复制到 shadow。"""
    prod = Path(prod_path) if prod_path else DEFAULT_DB_PATH
    shadow = Path(shadow_path) if shadow_path else SHADOW_DB_PATH
    if not prod.exists():
        raise FileNotFoundError(f"prod 数据库不存在: {prod}")
    shadow.parent.mkdir(parents=True, exist_ok=True)
    if shadow.exists() and not overwrite:
        return shadow
    shutil.copy2(prod, shadow)
    return shadow
