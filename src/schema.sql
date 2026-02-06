-- Option Wheel Tracker 数据库 Schema v2.0
-- 支持个人资产管理 + 投资追踪

-- ==================== 基础表 ====================

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'asset' | 'liability'
    category TEXT,      -- 'cash' | 'stock' | 'etf' | 'crypto' | 'a股' | 'hkd' | ' provident_fund' | 'receivable' | 'other'
    currency TEXT DEFAULT 'USD',
    balance REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 汇率表（按日存储）
CREATE TABLE IF NOT EXISTS exchange_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    currency TEXT NOT NULL,
    rate_to_usd REAL NOT NULL,  -- 1单位外币 = ? USD
    rate_to_rmb REAL NOT NULL,  -- 1单位外币 = ? RMB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, currency)
);

-- ==================== 交易表 ====================

-- 交易日志
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime TIMESTAMP NOT NULL,
    symbol TEXT,           -- 股票/标的代码
    action TEXT NOT NULL,  -- 'BUY' | 'SELL' | 'STO' (sell to open) | 'BTC' (buy to close) | 'ASSIGNMENT' | 'CALLED_AWAY' | 'DIVIDEND' | 'INCOME' | 'EXPENSE'
    quantity REAL,         -- 股数或期权张数
    price REAL,           -- 单价或权利金
    fees REAL DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    account_id INTEGER,
    category TEXT,         -- '投资' | '收入' | '支出'
    subcategory TEXT,     -- '股票' | '期权' | '工资' | '餐饮' | '房租' | etc.
    target TEXT,          -- 支出/收入对象（可选）
    note TEXT,
    strategy_id INTEGER,  -- 关联策略ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,             -- 'wheel' | 'value' | 'income' | 'other'
    symbol TEXT,
    status TEXT DEFAULT 'active',  -- 'active' | 'closed' | 'paused'
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 快照表 ====================

-- 资产快照
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    total_assets_usd REAL,
    total_assets_rmb REAL,
    assets_json TEXT,      -- 各资产详情 JSON
    is_latest INTEGER DEFAULT 0,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 年度汇总表 ====================

-- 年度收入/支出汇总
CREATE TABLE IF NOT EXISTS yearly_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    pre_tax_income REAL,      -- 税前收入
    social_insurance REAL,    -- 五险一金
    income_tax REAL,          -- 个人所得税
    post_tax_income REAL,     -- 税后收入
    investment_income REAL,   -- 理财收入
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year)
);

-- ==================== 期权专用表 ====================

-- 期权链
CREATE TABLE IF NOT EXISTS option_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    underlying TEXT NOT NULL,     -- 标的
    option_type TEXT NOT NULL,    -- 'put' | 'call'
    strike_price REAL NOT NULL,
    expiration_date DATE,
    quantity INTEGER,              -- 张数
    premium REAL NOT NULL,         -- 权利金（每股）
    fees REAL DEFAULT 0,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- ==================== 索引 ====================

CREATE INDEX IF NOT EXISTS idx_transactions_datetime ON transactions(datetime);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(date);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_date ON exchange_rates(date);
