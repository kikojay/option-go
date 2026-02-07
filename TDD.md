# 系统重构技术设计文档 (TDD)

> Wealth Tracker v3.0 — 从 0 到 1 重构  
> Author: Copilot · Date: 2026-02-07  
> Status: Draft

---

## 一、现状审计（Why）

### 1.1 代码腐化数据

| 指标 | 数值 | 评价 |
|------|------|------|
| 项目总行数 | ~9,000 行 | |
| 其中死文件行数 | ~4,700 行 Python + ~1,200 行死文档（共 65%） | 超过一半已废弃未清理 |
| `dict_to_transaction` 拷贝数 | 3 份 | 改一处忘两处 |
| `OPTION_ACTIONS` 等常量定义处 | 5+ | 各自独立，无 single source of truth |
| `FinanceEngine` 类行数 | 1,008 行 / 39 方法 / 7 个域 | God Object |
| `FinanceEngine` 与 `PortfolioService` 功能完全重复 | 15 项 | 两套并行计算逻辑 |
| `src/components.py` 反向依赖 `frontend/config.py` | 1 处 | 底层依赖上层 |
| 数据库中未使用的表 | 2 个（`option_legs`, `strategies`） | 死 Schema |
| 未使用的 `__init__.py` 导出 | 3 个模块 | 混淆导入路径 |

### 1.2 核心问题

1. **God Object**：`FinanceEngine` 混合了 7 个业务域（overview / snapshot / expense / trading / yearly / portfolio / wheel），1,008 行无法测试、无法复用。

2. **重复实现**：`FinanceEngine` 和 `PortfolioService` 对投资组合有 **完全一致的 15 个方法**（加载、指标、趋势、持仓、期权），两套代码不同步是时间问题。

3. **层级混乱**：`src/components.py` 在 `src/` 层级却 import `frontend/config.py`（UI 注入 CSS），打破了单向依赖原则。

4. **65% 死代码**：v1 入口（`app.py`）、旧数据库（`database.py`）、旧计算器（`calculator.py`、`charts.py`）、旧 UI（`src/ui/`）、旧可视化（`src/visualization/`）、旧 portfolio 页面共 ~4,700 行未清理。

5. **投资组合页面不稳定**：三个 Tab（总览趋势 / 持仓明细 / 期权策略）依赖 `PortfolioService`，同时期权 Tab 又自行构建 `WheelCalculator`——数据流不统一。

6. **常量散落**：同一组常量（交易操作/颜色/分类映射）在 5+ 个文件中各自定义，修改时极易遗漏。

7. **分类体系缺陷——记账与理财混在一起**：
   - Schema 中 `category` 只有 `'投资' | '收入' | '支出'` 三个值，没有代码级约束
   - `EXPENSE_CATEGORIES` 把 `"工资"` (收入)、`"投资"` (理财)、`"分红"` (理财收益) 和 `"餐饮"` (生活开支) 放在同一个列表
   - `action` 字段身兼两职：`BUY/SELL/STO` 属于交易操作，`INCOME/EXPENSE` 属于记账操作，共用同一列
   - `expense_prepare()` 靠硬编码的 `_INVEST_ACTIONS` 集合过滤投资记录——脆弱且易遗漏新增操作
   - **后果**：无法准确回答「这个月我生活花了多少」「理财赚了多少」，因为数据从入口就没分清楚

### 1.3 存活文件清单（重构基础）

**活跃核心代码（~5,100 行）**：

```
app_v2.py                         108 行  入口
frontend/config.py                252 行  配置
frontend/helpers.py               157 行  工具
frontend/page_overview.py          90 行  页面
frontend/page_snapshots.py        120 行  页面
frontend/page_yearly.py           100 行  页面
frontend/page_expense.py          125 行  页面
frontend/page_trading_log.py       80 行  页面
frontend/page_wheel.py            160 行  页面
frontend/page_settings.py          29 行  页面
frontend/portfolio/main.py         39 行  页面
frontend/portfolio/tab_overview.py 141 行  页面
frontend/portfolio/tab_holdings.py  55 行  页面
frontend/portfolio/tab_options.py  144 行  页面
src/finance_engine.py            1,008 行  引擎（含 250 行死代码）
src/components.py                 356 行  UI 组件
src/database_v2.py                399 行  数据层
src/services/portfolio_service.py 599 行  服务（与引擎重复）
src/models/transaction.py          75 行  模型
src/models/account.py              55 行  模型
src/models/campaign.py             56 行  模型
src/options/calculator.py         146 行  计算器
src/options/wheel_strategy.py     293 行  计算器
src/portfolio/calculator.py       140 行  计算器
src/portfolio/analyzer.py         200 行  分析器
api/exchange_rates.py              --     外部接口
api/stock_data.py                  --     外部接口
api/stock_names.py                 --     外部接口
```

---

## 二、目标架构（What）

### 2.1 设计原则

| # | 原则 | 实践 |
|---|------|------|
| 1 | **单向依赖** | `page → service → repository → db`，永远不逆向 |
| 2 | **Single Source of Truth** | 每个常量、模型、转换函数只存在一处 |
| 3 | **单一职责** | 每个模块 < 300 行，每个类 < 200 行 |
| 4 | **面向接口** | Service 方法返回 `TypedDict` / `dataclass`，不返回裸 dict |
| 5 | **可测试** | Service / Repository 不依赖 Streamlit，可单元测试 |
| 6 | **零死代码** | 删除所有 v1 遗留，不保留"兼容层" |
| 7 | **Streamlit 感知** | 理解 Streamlit 每次交互全脚本重跑的执行模型，用 Session State + Cache 消除冗余计算 |

### 2.2 目录结构

```
option-go/
├── app.py                        # 唯一入口（≤80 行）
├── requirements.txt
├── README.md
│
├── config/                       # 全局配置（Single Source of Truth）
│   ├── __init__.py               # 导出所有配置
│   ├── constants.py              # 交易操作/分类常量（OPTION_ACTIONS 等）
│   ├── theme.py                  # 颜色、CSS、Plotly 布局
│   └── labels.py                 # 中文映射（ACTION_CN 等）
│
├── models/                       # 数据模型 (dataclass)
│   ├── __init__.py
│   ├── transaction.py            # Transaction dataclass
│   ├── account.py                # Account dataclass
│   ├── snapshot.py               # Snapshot dataclass
│   └── converters.py             # dict_to_transaction — 唯一一份
│
├── db/                           # 数据访问层（纯 CRUD）
│   ├── __init__.py
│   ├── connection.py             # 连接管理 + schema 初始化
│   ├── transactions.py           # 交易 CRUD
│   ├── accounts.py               # 账户 CRUD
│   ├── exchange_rates.py         # 汇率 CRUD
│   ├── snapshots.py              # 快照 CRUD
│   └── yearly.py                 # 年度汇总 CRUD
│
├── services/                     # 业务逻辑层（按域拆分）
│   ├── __init__.py
│   ├── overview.py               # 总览指标/趋势（预留 fx_mode 参数）
│   ├── snapshot.py               # 快照汇总/详情
│   ├── expense.py                # 收支统计
│   ├── trading.py                # 交易日志统计
│   ├── yearly.py                 # 年度数据
│   ├── portfolio.py              # 投资组合（预留 net_inflow 接口）
│   └── wheel.py                  # 期权车轮策略
│
├── calculators/                  # 纯计算器（无 DB、无 Streamlit）
│   ├── __init__.py
│   ├── portfolio_calc.py         # 持仓计算 (PortfolioCalculator)
│   ├── option_calc.py            # 期权定价 (OptionCalculator)
│   ├── wheel_calc.py             # 车轮策略 (WheelStrategyCalculator)
│   ├── fx_calc.py                # 汇率归因分解 (FXCalculator) ← 预留
│   └── fire_calc.py              # 退休模拟 (FIRECalculator) ← 预留
│
├── api/                          # 外部数据接口
│   ├── __init__.py
│   ├── exchange_rates.py         # 汇率 + 缓存
│   ├── stock_prices.py           # 行情（yfinance）← 原 stock_data.py 改名
│   └── stock_names.py            # 股票名称
│
├── ui/                           # UI 组件库
│   ├── __init__.py
│   ├── components.py             # UI 原子组件（card / table / metric_row）
│   └── charts.py                 # Plotly 图表封装
│
├── pages/                        # 视图层
│   ├── __init__.py
│   ├── overview.py               # 总览
│   ├── snapshots.py              # 月度快照
│   ├── yearly.py                 # 年度汇总
│   ├── expense.py                # 收支管理
│   ├── trading.py                # 交易日志
│   ├── wheel.py                  # 期权车轮
│   ├── settings.py               # 设置
│   └── portfolio/                # 投资组合
│       ├── __init__.py
│       ├── main.py
│       ├── tab_overview.py
│       ├── tab_holdings.py
│       └── tab_options.py
│
├── scripts/
│   └── seed_mock_data.py          # Mock 数据生成脚本
│
├── data/
│   ├── wealth.db                 # SQLite（自动创建）
│   └── cache/                    # API 缓存
│
└── tests/
    ├── test_services/
    │   ├── test_overview.py
    │   ├── test_expense.py
    │   ├── test_portfolio.py
    │   └── test_wheel.py
    └── test_calculators/
        ├── test_portfolio_calc.py
        └── test_wheel_calc.py
```

### 2.3 Streamlit 会话状态（Session State）管理

> **Streamlit 的执行模型**：每次用户交互（点击按钮、切换页面、勾选框）都会**从头到尾重跑整个 `app.py`**。如果不做状态管理，所有中间计算结果、用户选择、API 数据全部丢失重来。

#### 2.3.1 状态分层

| 层 | 名称 | 生命周期 | 示例 |
|----|------|----------|------|
| L0 | **全局不可变** | App 启动时初始化一次 | 数据库 Schema 版本、应用标题 |
| L1 | **会话共享数据** | 用户首次访问时加载，跨页面共享 | 汇率 `rates`、账户列表 `accounts` |
| L2 | **页面内状态** | 页面切换时重置 | 选中的 symbol、当前 Tab index |
| L3 | **用户操作状态** | 手动触发时更新 | 表单输入、编辑中的行 |

#### 2.3.2 App 入口状态初始化

```python
# app.py — 在路由之前执行

def init_session_state():
    """初始化会话状态（仅在首次执行时生效）"""

    # L1: 汇率（跨页面共享，避免每个页面都重新请求 API）
    if "rates" not in st.session_state:
        st.session_state.rates = get_exchange_rates()
    
    # L1: 汇率派生快捷值
    if "usd_rmb" not in st.session_state:
        rates = st.session_state.rates
        st.session_state.usd_rmb = rates["USD"]["cny"]
        st.session_state.hkd_rmb = rates["HKD"]["cny"]

    # L1: 账户列表
    if "accounts" not in st.session_state:
        st.session_state.accounts = db.accounts.get_all()

    # L1: 当前页面标识（用于检测页面切换）
    if "current_page" not in st.session_state:
        st.session_state.current_page = None
```

#### 2.3.3 页面切换感知

```python
# app.py — 路由逻辑

def main():
    init_session_state()
    page = st.sidebar.radio("导航", PAGES)

    # 检测页面切换，清理上一个页面的 L2 状态
    if st.session_state.current_page != page:
        _clear_page_state(st.session_state.current_page)
        st.session_state.current_page = page

    PAGES[page]()  # 调用对应页面的 render()

def _clear_page_state(old_page: str | None):
    """清理上一个页面的 L2 级状态"""
    prefix = f"page_{old_page}_" if old_page else ""
    keys_to_remove = [k for k in st.session_state if k.startswith(prefix)]
    for k in keys_to_remove:
        del st.session_state[k]
```

#### 2.3.4 页面内状态命名规范

```python
# 所有页面内状态使用 "page_{页面名}_{字段}" 命名
# 例: page_wheel_selected_symbol, page_portfolio_tab_index

# pages/wheel.py 示例
def render():
    # L2: 当前选中的 symbol（页面切换时自动清理）
    if "page_wheel_selected_symbol" not in st.session_state:
        st.session_state.page_wheel_selected_symbol = None
    
    # L1: 汇率从 session_state 读取，不重新请求
    usd_rmb = st.session_state.usd_rmb
    
    data = WheelService.load(usd_rmb)
    ...
```

#### 2.3.5 汇率刷新机制

```python
# 汇率不需要每次交互都刷新，但用户可以手动刷新

# pages/settings.py 或侧栏
if st.button("🔄 刷新汇率"):
    st.session_state.rates = get_exchange_rates()
    st.session_state.usd_rmb = st.session_state.rates["USD"]["cny"]
    st.session_state.hkd_rmb = st.session_state.rates["HKD"]["cny"]
    st.rerun()
```

### 2.4 依赖关系图

```
┌─────────────────────────────────────────────────────┐
│                    pages/ (视图层)                    │
│  只做: 路由 + 调用 service + 调用 ui                  │
└────────────────────────┬────────────────────────────┘
                         │ 调用
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ services/  │ │   ui/      │ │  config/   │
   │  业务逻辑  │ │ 渲染组件   │ │ 常量/主题  │
   └──────┬─────┘ └────────────┘ └────────────┘
          │ 调用                    ▲ 引用
    ┌─────┼─────┐                  │
    ▼     ▼     ▼                  │
 ┌─────┐┌────┐┌─────────────┐     │
 │ db/ ││api/││calculators/ │─────┘
 │CRUD ││外部││  纯计算     │
 └──┬──┘└────┘└─────────────┘
    ▼
 ┌────────┐
 │ models │
 └────────┘
```

**规则**：
- `pages/` → `services/` + `ui/` + `config/`（可以调用）
- `services/` → `db/` + `api/` + `calculators/` + `config/` + `models/`（可以调用）
- `ui/` → `config/`（只引用主题）
- `db/` → `models/`（只引用模型）
- **绝对禁止**：`services/` → `ui/`、`db/` → `services/`、任何层 → `pages/`

### 2.6 数据库 Schema 精简

```sql
-- 保留 5 个核心表

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

-- 保留 exchange_rates 表（VPS 多设备并发安全）
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
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            DATE NOT NULL,
    total_assets_usd REAL,
    total_assets_rmb REAL,
    assets_json     TEXT,
    note            TEXT
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
```

**变更**：
- 删除 `option_legs`（未使用）
- 删除 `strategies`（未使用）
- **保留 `exchange_rates` 表**（见下方说明）
- 删除 `transactions.strategy_id`、`transactions.target` 列
- 添加 5 个索引（`action`, `category`, `symbol`, `datetime`, `exchange_rates.date`）
- 删除 `snapshots.is_latest`（冗余）

#### 2.6.1 汇率存储策略：DB + 文件缓存双写

> **为什么不能只用文件缓存？**
> 
> 该应用部署在 VPS 上，可能多设备（手机/电脑）通过 PWA 同时访问。
> JSON 缓存文件没有并发锁机制——两个 Streamlit Session 同时写同一个 JSON 文件可能导致数据损坏。
> SQLite 自带 WAL 模式的并发写保护，更适合做数据持久层。

**双层策略**：

```
┌─────────────────────┐
│   Session State     │  ← L1: 内存，每个Session一份，最快
│   st.session_state  │
│   .rates            │
└────────┬────────────┘
         │ 首次加载 (miss)
         ▼
┌─────────────────────┐
│   exchange_rates 表  │  ← L2: SQLite，进程安全，TTL=1小时
│   (date+currency)   │
└────────┬────────────┘
         │ 过期 (miss)
         ▼
┌─────────────────────┐
│   ExchangeRate API   │  ← L3: 外部HTTP，按需刷新
│   exchangerate-api   │
└─────────────────────┘
```

**查询流程**：
1. 先看 `st.session_state.rates`（L1，0ms）
2. L1 miss → 查 `exchange_rates` 表当天记录（L2，< 1ms）
3. L2 miss / 过期 → 调 API 获取最新汇率（L3，~200ms），写回 L2 + L1
4. **fallback**: L3 失败 → 用 L2 最近一条记录；L2 也空 → 用硬编码默认值

**服务端实现**：

```python
# api/exchange_rates.py

def get_exchange_rates() -> dict:
    """三级缓存查询汇率"""
    # L2: 查 DB
    today = date.today().isoformat()
    cached = db.exchange_rates.get_by_date(today)
    if cached:
        return _format_rates(cached)
    
    # L3: 调 API
    try:
        rates = _fetch_from_api()
        db.exchange_rates.upsert(today, rates)  # 写回 L2
        return rates
    except Exception:
        # fallback: 查最近一条
        latest = db.exchange_rates.get_latest()
        return _format_rates(latest) if latest else _DEFAULTS
```

**同时保留 `data/cache/` 目录中的 JSON 文件**作为极端 fallback（DB 损坏时），但正常流程不依赖它。

### 2.7 缓存与渲染性能策略

> **Streamlit 的性能杀手**：每次用户交互都重跑全脚本。如果每次都查 DB → 计算 → 渲染，一个有 500 条交易记录的用户切换 Tab 就要等 2-3 秒。

#### 2.7.1 三级缓存架构

| 级别 | 机制 | TTL | 适用场景 | 击穿方式 |
|------|------|-----|----------|----------|
| L1 | `st.session_state` | 当前会话 | 汇率、账户列表、用户选择 | 手动刷新按钮 |
| L2 | `@st.cache_data(ttl=N)` | N 秒 | Service 层查询结果（全部 Session 共享） | TTL 过期 / `st.cache_data.clear()` |
| L3 | SQLite / API | 持久化 | 原始数据 | 用户操作（新增/编辑交易） |

#### 2.7.2 Service 层缓存规则

```python
# services/overview.py

import streamlit as st

class OverviewService:
    @staticmethod
    @st.cache_data(ttl=600)  # 10 分钟缓存
    def get_metrics(usd_rmb: float, hkd_rmb: float) -> OverviewMetrics:
        """缓存总览指标，汇率变化时自动失效（因为参数变了）"""
        ...

    @staticmethod
    @st.cache_data(ttl=600)
    def get_trend() -> pd.DataFrame | None:
        """缓存趋势数据"""
        ...
```

**关键点**：`@st.cache_data` 以函数参数作为 cache key。当 `usd_rmb` 值变化（用户刷新汇率），缓存自动失效重新计算——不需要手动清缓存。

#### 2.7.3 各 Service 缓存一览

| Service | 方法 | TTL | 理由 |
|---------|------|-----|------|
| `OverviewService.get_metrics()` | 600s | 总览数据变化频率低，但依赖汇率参数 |
| `OverviewService.get_trend()` | 600s | 趋势图数据量大，不必每次重算 |
| `PortfolioService.load()` | 300s | 持仓数据 + 实时股价，5 分钟合理 |
| `WheelService.load()` | 300s | 同上 |
| `ExpenseService.get_monthly()` | 600s | 收支数据变化频率低 |
| `SnapshotService.get_all()` | 3600s | 快照很少变化 |
| `YearlyService.get_all()` | 3600s | 年度汇总基本不变 |
| `TradingService.get_log()` | 300s | 新增交易后需要较快刷新 |

#### 2.7.4 缓存失效：写操作后主动清除

```python
# 当用户新增交易后，主动清除相关缓存
def on_transaction_added():
    """交易新增后的回调"""
    # 清除受影响的 service 缓存
    OverviewService.get_metrics.clear()
    PortfolioService.load.clear()
    WheelService.load.clear()
    TradingService.get_log.clear()
    st.rerun()
```

#### 2.7.5 DB 连接缓存

```python
# db/connection.py
import streamlit as st

@st.cache_resource
def get_connection():
    """缓存数据库连接（进程级别，不会每次交互重建连接）"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # WAL 模式支持并发读
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

> **`@st.cache_resource` vs `@st.cache_data`**：
> - `cache_resource`：缓存不可序列化的对象（DB 连接、ML 模型），全局单例
> - `cache_data`：缓存可序列化的计算结果（DataFrame、dict），按参数隔离

#### 2.7.6 前端渲染优化

| 优化项 | 方案 | 影响 |
|--------|------|------|
| Plotly 图表加载慢 | 使用 `st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})` 减少前端 JS 开销 | 图表渲染快 30% |
| 大表格滚动卡顿 | 交易记录 > 100 条时使用分页 `st.dataframe(df.head(50))` + "加载更多" 按钮 | 避免 DOM 爆炸 |
| 多个图表同时渲染 | 使用 `st.tabs` / `st.expander` 懒加载——折叠的区块不渲染图表 | 减少初始加载 |
| CSS 注入重复 | `inject_css()` 用 `st.session_state._css_injected` 标记，只注入一次 | 减少 DOM 操作 |

### 2.8 业务域划分与分类隔离

> **核心理念**：用户的三大需求（资产追踪 / 日常记账 / 投资监控）必须在**数据层**就彻底隔离，而不是在 UI 层用 filter 来分流。

#### 2.8.1 三大业务域

```
┌─────────────────────────────────────────────────────────────────┐
│                    Wealth Tracker v3.0                          │
├─────────────────┬───────────────────┬──────────────────────────┤
│    域 1          │     域 2          │       域 3               │
│  资产追踪        │   日常记账         │     投资监控             │
│  Asset Tracking  │   Accounting      │   Investment            │
├─────────────────┼───────────────────┼──────────────────────────┤
│ • 总览仪表盘     │ • 月度收支明细     │ • 股票持仓              │
│ • 资产快照       │ • 年度收支汇总     │ • 盈亏分析              │
│ • 趋势图         │ • 分类饼图         │ • 期权车轮策略           │
│ • 类别占比       │ • 存率计算         │ • 交易日志              │
├─────────────────┼───────────────────┼──────────────────────────┤
│ 数据来源:        │ 数据来源:          │ 数据来源:               │
│ snapshots 表     │ transactions 表   │ transactions 表         │
│ accounts 表      │ category=INCOME   │ category=INVESTMENT     │
│                  │ category=EXPENSE  │ category=TRADING        │
└─────────────────┴───────────────────┴──────────────────────────┘
```

**关键边界规则**：
- 「我每月工资 2 万」= **INCOME**，永远不进投资计算
- 「我往券商入金 5 万」= **INVESTMENT**（本金转移），不算「支出」
- 「卖 Put 收权利金 $500」= **TRADING**（交易盈亏），不算「收入」
- 「收到 AAPL 分红 $50」= **TRADING**（投资收益），不算「工资收入」
- 「吃饭花了 ¥200」= **EXPENSE**，永远不影响投资统计

#### 2.8.2 `config/constants.py` — 分类常量严格定义

```python
# config/constants.py

from enum import Enum
from typing import FrozenSet

# ═══════════════════════════════════════════════════════
#  交易分类 — Single Source of Truth
# ═══════════════════════════════════════════════════════

class TransactionCategory(str, Enum):
    """交易记录的一级分类（互斥，不可交叉）"""
    INCOME     = "INCOME"       # 收入（工资、奖金、副业）
    EXPENSE    = "EXPENSE"      # 支出（生活开销）
    INVESTMENT = "INVESTMENT"   # 投资本金进出（入金/出金）
    TRADING    = "TRADING"      # 交易操作（买卖/期权/分红）


# ── 二级分类（subcategory）──────────────────────────────

# 收入子分类
INCOME_SUBCATEGORIES = [
    "工资", "奖金", "副业", "退税", "礼金", "其他收入",
]

# 支出子分类
EXPENSE_SUBCATEGORIES = [
    "餐饮", "房租", "交通", "日用", "外食", "在家吃饭",
    "订阅", "家庭", "医疗", "娱乐", "教育", "其他支出",
]

# 投资子分类（本金流动）
INVESTMENT_SUBCATEGORIES = [
    "入金", "出金",
]

# 交易子分类（买卖操作产生的记录）
TRADING_SUBCATEGORIES = [
    "股票", "期权", "分红", "ETF",
]

# 分类 → 子分类 映射（用于表单校验）
CATEGORY_SUBCATEGORIES = {
    TransactionCategory.INCOME:     INCOME_SUBCATEGORIES,
    TransactionCategory.EXPENSE:    EXPENSE_SUBCATEGORIES,
    TransactionCategory.INVESTMENT: INVESTMENT_SUBCATEGORIES,
    TransactionCategory.TRADING:    TRADING_SUBCATEGORIES,
}


# ── 操作类型（action）按域分组 ────────────────────────

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


# ── action → category 自动推断 ────────────────────────

def infer_category(action: str) -> TransactionCategory:
    """根据 action 自动推断一级 category（入库时调用）"""
    if action in ACCOUNTING_ACTIONS:
        return TransactionCategory.INCOME if action == "INCOME" else TransactionCategory.EXPENSE
    if action in CAPITAL_ACTIONS:
        return TransactionCategory.INVESTMENT
    if action in (STOCK_ACTIONS | OPTION_ACTIONS | YIELD_ACTIONS):
        return TransactionCategory.TRADING
    raise ValueError(f"未知操作类型: {action}，合法值: {ALL_ACTIONS}")
```

#### 2.8.3 数据流隔离示意

```
用户操作               action          category (自动推断)
─────────────────      ──────          ──────────────────
记一笔工资         →   INCOME      →   INCOME
记一笔房租         →   EXPENSE     →   EXPENSE
往券商入金         →   DEPOSIT     →   INVESTMENT
从券商出金         →   WITHDRAW    →   INVESTMENT
买入 AAPL 100股    →   BUY         →   TRADING
卖出 Put           →   STO         →   TRADING
收到 AAPL 分红     →   DIVIDEND    →   TRADING
被行权接盘         →   ASSIGNMENT  →   TRADING
```

**Service 层查询时直接按 category 过滤**：

```python
# services/expense.py — 只碰 INCOME + EXPENSE
def load():
    return db.transactions.query(
        category_in=[TransactionCategory.INCOME, TransactionCategory.EXPENSE]
    )

# services/portfolio.py — 只碰 TRADING + INVESTMENT
def load():
    return db.transactions.query(
        category_in=[TransactionCategory.TRADING, TransactionCategory.INVESTMENT]
    )

# services/wheel.py — 只碰 TRADING
def load():
    return db.transactions.query(
        category_in=[TransactionCategory.TRADING],
        action_in=OPTION_ACTIONS | STOCK_ACTIONS | YIELD_ACTIONS
    )
```

**不再需要 `_INVEST_ACTIONS` 这种脆弱的反向过滤**。每个 Service 正向声明自己关心的 category，新增操作类型时不会影响其他域。

#### 2.8.4 数据库层强制约束

`transactions` 表的 `action` 和 `category` 字段均带 CHECK 约束（已在 §2.6 Schema 中定义），SQLite 层面直接拒绝非法写入。

#### 2.8.5 页面 → 域 映射

| 页面 | 业务域 | 读取的 category | Service |
|------|--------|-----------------|--------|
| 总览 | 资产追踪 | snapshots + accounts | `OverviewService` |
| 快照 | 资产追踪 | snapshots | `SnapshotService` |
| 收支管理 | 日常记账 | INCOME + EXPENSE | `ExpenseService` |
| 年度汇总 | 日常记账 + 资产追踪 | yearly_summary + snapshots | `YearlyService` |
| 投资组合 | 投资监控 | TRADING + INVESTMENT | `PortfolioService` |
| 交易日志 | 投资监控 | TRADING + INVESTMENT | `TradingService` |
| 车轮策略 | 投资监控 | TRADING | `WheelService` |
| 设置 | 全局 | accounts | `SettingsService` |

### 2.9 可扩展性设计

> 当前架构是否能支持未来需求扩展？

#### 2.9.1 当前架构可直接支持的扩展

| 未来需求 | 扩展方式 | 改动范围 |
|----------|----------|----------|
| 新增资产类型（如基金、房产） | `accounts.category` 加一个值 + `CATEGORY_CN` 加映射 | 1 处常量 |
| 新增支出子分类（如宠物、旅行） | `EXPENSE_SUBCATEGORIES` 加一项 | 1 处常量 |
| 新增交易操作（如 `SELL_CALL_SPREAD`） | `OPTION_ACTIONS` 加一项 + `ACTION_CN` 加映射 | 2 处常量 |
| 加密货币追踪 | 新建 `services/crypto.py` + `pages/crypto.py` | 新文件，不改旧代码 |
| 税务报表导出 | 新建 `services/tax_report.py`，按 category 分别统计 | 新文件 |
| 多币种支出记账 | `ExpenseService` 已有 `currency` 字段 + `usd_rmb` 换算 | 0 改动 |
| Telegram Bot 通知 | 新建 `integrations/telegram.py`，监听 Service 事件 | 新文件 |
| **净投入追踪** | 实现 `PortfolioService.get_net_inflow()` 方法体 | 1 个方法（接口已预留） |
| **汇率归因分析** | 实现 `FXCalculator` + `get_metrics(fx_mode=...)` | 1 个 Calculator + 1 个参数 |
| **FIRE 退休模拟** | 实现 `FIRECalculator` + 新增 `pages/fire.py` | 1 个 Calculator + 1 页面 |

#### 2.9.2 架构保护点

1. **分类严格隔离** → 新增域（如加密货币）只需增加一个 `TransactionCategory` 枚举值，不影响现有域
2. **Service 正向过滤** → 每个 Service 显式声明关心的 category，新增 category 不会"污染"已有 Service
3. **Calculator 纯函数** → 计算逻辑无 DB/UI 依赖，可被任何新 Service 复用
4. **页面 ≤ 120 行** → 新增页面成本极低（复制模式 + 接入对应 Service）
5. **Config SSOT** → 新增常量只改 `config/` 一处，全系统生效

#### 2.9.3 当前架构不支持（需二期重构）的扩展

| 需求 | 原因 | 二期方案 |
|------|------|----------|
| 多用户/账户隔离 | 当前 SQLite 无用户概念 | 迁移 PostgreSQL + 加 user_id 外键 |
| 实时股价推送 | Streamlit 无 WebSocket | 考虑 Server-Sent Events 或轮询 |
| 移动端原生体验 | PWA 有局限 | React Native 前端 + API 后端 |

### 2.10 前瞻性能力预留（记账本 → 私人财务顾问）

> 以下 3 个维度不在 Phase 0-7 中实现，但在 Service/Calculator 架构中**提前预留接口和数据通路**，确保未来迭代时零重构接入。

#### 2.10.1 资金流向与净投入追踪（Net Inflow Tracking）

**问题**：重构后能算"赚了多少"，但无法直观回答**"我一共存了多少本金进去"**。

- 工资收入（INCOME）→ 生活开销（EXPENSE）→ 结余 → 入金（INVESTMENT/DEPOSIT）→ 投资（TRADING）
- 投资利润留存 vs 本金追加，对计算"真实投资回报率"至关重要

**预留设计**：

```python
# services/portfolio.py — 净投入追踪（预留接口）

class PortfolioService:
    @staticmethod
    def get_net_inflow() -> NetInflowMetrics:
        """
        计算净投入：
        - total_deposited:  历史累计入金总额（DEPOSIT）
        - total_withdrawn:  历史累计出金总额（WITHDRAW）
        - net_inflow:       净投入 = deposited - withdrawn
        - current_value:    当前投资组合市值
        - profit_retained:  利润留存 = current_value - net_inflow
        - true_return_rate: 真实回报率 = profit_retained / net_inflow
        """
        ...

    @staticmethod
    def get_savings_to_invest_ratio(
        expense_monthly: float, net_inflow_monthly: float
    ) -> float:
        """
        储蓄转化率：每月结余中有多少流入了投资账户？
        = net_inflow_monthly / (income_monthly - expense_monthly)
        """
        ...
```

**数据通路**：
```
ExpenseService.get_monthly()        → 月均生活成本
         ↓
PortfolioService.get_net_inflow()   → 净投入 / 真实回报率
         ↓
RetirementSimulator (2.10.3)        → SWR 安全提款率计算
```

**为什么现在就能预留**：`INVESTMENT` category 的 `DEPOSIT/WITHDRAW` 操作已经在 §2.8 严格隔离，`services/portfolio.py` 只需要 `SUM(DEPOSIT) - SUM(WITHDRAW)` 就能算出净投入。

---

#### 2.10.2 汇率幻觉抵扣（FX Neutralization）

**问题**：你有约 35% 的美股资产。如果这个月美元兑人民币从 7.1 涨到 7.3，你的"总资产"增长了 2.8%——但这不是真正的投资收益，只是汇率波动的幻觉。

**预留设计**：

```python
# services/overview.py — 双视角资产计算

class OverviewService:
    @staticmethod
    def get_metrics(
        usd_rmb: float,
        hkd_rmb: float,
        fx_mode: str = "current"     # "current" | "fixed" | "entry"
    ) -> OverviewMetrics:
        """
        fx_mode 参数控制汇率视角：
        - "current":  用实时汇率折算（默认，即现有行为）
        - "fixed":    用固定基准汇率折算（如 7.0），屏蔽汇率波动
        - "entry":    用每笔交易入场时的汇率折算（最精确）
        """
        ...

# calculators/fx_calc.py — 汇率归因（纯计算器）

class FXCalculator:
    @staticmethod
    def decompose_return(
        entries: list[dict],        # 每笔交易 {date, amount_usd, fx_rate_at_entry}
        current_value_usd: float,
        current_fx: float,
    ) -> FXDecomposition:
        """
        将总收益分解为：
        - asset_return:   标的本身涨跌贡献（本币不变时的收益）
        - fx_return:      汇率波动贡献（标的不变时的收益）
        - total_return:   总收益 = asset_return + fx_return + 交叉项
        """
        ...
```

**数据通路**：
```
db/transactions.py                  → 每笔交易的 currency + 入场日期
         ↓
db/exchange_rates.py                → 历史汇率（date + currency）
         ↓
FXCalculator.decompose_return()     → 收益归因：标的 vs 汇率
         ↓
pages/overview.py                   → 切换按钮："实时汇率 / 固定基准"
```

**为什么现在就能预留**：
- `exchange_rates` 表已保留（§2.6.1），历史汇率数据具备
- 每笔交易有 `currency` + `datetime` 字段，可以反查入场汇率
- `get_metrics()` 只需多加一个 `fx_mode` 参数，默认 `"current"` 不影响现有行为

---

#### 2.10.3 压力测试与退休模拟（FIRE Simulation）

**问题**：工具目前是纯"回顾性"的——看过去发生了什么。缺乏"预测性"——按当前轨迹，我的资产几年后会怎样？

**预留设计**：

```python
# calculators/fire_calc.py — 退休模拟器（纯计算器，无 DB 依赖）

from dataclasses import dataclass
from typing import List

@dataclass
class FIREProjection:
    """单一情景的投影结果"""
    annual_return: float        # 假设年化收益率
    years_to_fire: int | None   # 达到 FIRE 的年数（None=无法达到）
    years_to_zero: int | None   # 资产归零的年数（None=永不归零）
    trajectory: List[dict]      # [{year, assets, income, expense, net}]


class FIRECalculator:
    @staticmethod
    def project(
        current_assets: float,          # 当前总资产（来自 OverviewService）
        monthly_expense: float,         # 月均支出（来自 ExpenseService）
        monthly_income: float,          # 月均主动收入（来自 ExpenseService）
        monthly_investment: float,      # 月均投资额（来自 PortfolioService.net_inflow）
        annual_return_rates: list[float] = [0.04, 0.07, 0.10],  # 情景：4%, 7%, 10%
        inflation_rate: float = 0.03,   # 通胀率
        swr: float = 0.04,             # 安全提款率 (Safe Withdrawal Rate)
    ) -> list[FIREProjection]:
        """
        对每个年化收益率情景，投影未来 50 年：
        
        FIRE 线 = monthly_expense × 12 / swr
                 = 年开销 / 安全提款率
                 = 例：¥10万/年 ÷ 4% = ¥250万
        
        每年:
          assets = assets * (1 + return) + investment * 12 - expense * 12
          如果 assets >= FIRE 线 → 达到财务自由
          如果 assets <= 0 → 资产归零
        """
        ...

    @staticmethod
    def sensitivity_table(
        current_assets: float,
        monthly_expense: float,
        return_range: list[float],      # [0.02, 0.04, 0.06, 0.08, 0.10]
        expense_change: list[float],    # [-0.2, -0.1, 0, 0.1, 0.2]  支出变动
    ) -> dict:
        """
        敏感性分析矩阵：
        纵轴 = 年化收益率
        横轴 = 支出变动幅度
        单元格 = 达到 FIRE 的年数
        
        帮助回答：如果我每月多省 2000，能提前几年退休？
        """
        ...
```

**数据通路**：
```
ExpenseService.get_monthly()            → 月均支出 / 月均收入
         ↓
PortfolioService.get_net_inflow()       → 月均投资额
         ↓
OverviewService.get_metrics()           → 当前总资产
         ↓
FIRECalculator.project()                → 退休投影 × 3 情景
         ↓
pages/fire.py (未来)                    → 折线图 + 敏感性热力图
```

**为什么现在就能预留**：
- `FIRECalculator` 是纯计算器（无 DB、无 Streamlit），放在 `calculators/` 目录即可
- 输入全部来自已有 Service 的返回值
- 未来新增 `pages/fire.py` 只需调用 Calculator + 渲染图表

---

#### 2.10.4 预留总结

| 能力 | 预留位置 | 一期改动 | 未来接入成本 |
|------|----------|----------|-------------|
| 净投入追踪 | `services/portfolio.py` | `get_net_inflow()` 方法签名 | 实现方法体 + 页面展示 |
| 汇率归因 | `services/overview.py` + `calculators/fx_calc.py` | `fx_mode` 参数 + Calculator 空壳 | 实现分解算法 + 页面切换按钮 |
| FIRE 模拟 | `calculators/fire_calc.py` | dataclass + 方法签名 | 实现投影算法 + 新增 `pages/fire.py` |

**一期只做接口预留（方法签名 + 注释），不实现方法体**。确保数据通路打通、依赖方向正确。

---

## 三、重构策略（How）

### 3.1 分阶段执行

| 阶段 | 内容 | 风险 | 预计工作量 |
|------|------|------|-----------|
| **Phase 0** | 删除全部死文件（~4,700 行代码 + ~1,200 行文档） | 低 | 10 分钟 |
| **Phase 1** | 抽取 `config/`（常量/主题/标签 SSOT + `TransactionCategory` 枚举 + 分类隔离常量） | 低 | 40 分钟 |
| **Phase 2** | 统一 `models/`，单一 `converters.py` | 中 | 30 分钟 |
| **Phase 3** | 拆 `db/`（从 `database_v2.py` 拆为 6 个文件 + Schema 加 CHECK 约束） | 中 | 40 分钟 |
| **Phase 4** | 拆 `services/`（合并 FinanceEngine + PortfolioService → 7 个域服务，每个 Service 严格声明自己的 category 范围） | 高 | 2 小时 |
| **Phase 5** | 重整 `ui/`（解除对 frontend 的反向依赖） | 中 | 30 分钟 |
| **Phase 6** | 重写 `pages/`（适配新 service 接口） | 中 | 1 小时 |
| **Phase 7** | 修复投资组合 Tab 页 + 重建 Mock 数据 + 端到端验证 | 高 | 1 小时 |

### 3.2 Phase 0：清理死文件

**删除清单**（共 20 个文件/目录）：

```
# v1 入口和遗留
app.py                          527 行
app_v2_old.py                 1,276 行

# v1 数据库和计算
src/database.py                 377 行
src/calculator.py               293 行
src/charts.py                   247 行
src/models.py                    87 行  ← 与 src/models/ 目录冲突
src/schema.sql                  117 行  ← Schema 迁入 db/connection.py

# v1 整合/通知
src/telegram_handler.py         315 行
src/integrations/               整个目录（8 行）
src/database/                   整个目录（43 行）
src/trading/                    整个目录（5 行，空壳）

# v1 旧 UI
src/ui/                         整个目录（234 行）

# v1 可视化
src/visualization/              整个目录（436 行）

# 旧 portfolio 单文件页面
frontend/page_portfolio.py      645 行  ← 已被 frontend/portfolio/ 替代

# 过时测试
test_calculator_fixes.py        192 行
tests/test_option_strategy.py   439 行  ← 重构后重写

# 过时文档
ARCHITECTURE.md                 365 行
FRONTEND.md                     344 行
MIGRATION.md                    255 行
UPDATES.md                      253 行
```

**合计**：Python ~4,700 行 + 文档 ~1,200 行 = **~5,900 行删除**

### 3.3 Phase 4 关键决策：合并 FinanceEngine + PortfolioService

**现状**：两套完全重复的投资组合逻辑。

**方案**：保留 `PortfolioService` 的实现（更成熟，被活跃页面使用），删除 `FinanceEngine` 中的 portfolio_*/option_* 方法（250 行死代码），将 `FinanceEngine` 剩余逻辑按域拆到 `services/` 下。

```
FinanceEngine (1,008 行)
├── 通用工具 (L85-163)     → models/converters.py
├── overview_* (L168-234)  → services/overview.py
├── snapshot_* (L238-306)  → services/snapshot.py
├── expense_* (L310-385)   → services/expense.py
├── trading_* (L388-425)   → services/trading.py
├── yearly_* (L428-449)    → services/yearly.py
├── portfolio_* (L452-694) → 删除（已有 PortfolioService）
├── wheel_* (L699-939)     → services/wheel.py
└── 辅助函数 (L941-1008)   → services/wheel.py (内部辅助)

PortfolioService (599 行)  → services/portfolio.py（重命名移入）
```

### 3.4 Service 层接口设计

每个 service 是纯函数集合（`@staticmethod`），不维护实例状态。参数显式传入，返回 `TypedDict`。

```python
# services/overview.py 示例结构

from typing import TypedDict, List

class OverviewMetrics(TypedDict):
    total_rmb: float
    total_usd: float
    total_cny: float
    delta_percent: float | None
    accounts: list[dict]
    cat_breakdown: list[dict]

class OverviewService:
    @staticmethod
    def get_metrics(usd_rmb: float, hkd_rmb: float) -> OverviewMetrics:
        """计算总览页面的核心指标。"""
        ...

    @staticmethod
    def get_trend() -> pd.DataFrame | None:
        """构建资产趋势 DataFrame。"""
        ...
```

```python
# services/portfolio.py 示例结构

class PortfolioService:
    @staticmethod
    def load(usd_rmb: float) -> PortfolioData | None:
        """加载投资组合完整数据。"""
        ...

    @staticmethod
    def overview_metrics(data: PortfolioData) -> OverviewMetrics:
        ...

    @staticmethod
    def holdings_rows(data: PortfolioData) -> list[dict]:
        ...

    @staticmethod
    def option_detail(data: PortfolioData, symbol: str) -> OptionDetail:
        ...
```

### 3.5 UI 层解耦

**问题**：`src/components.py` 导入 `frontend/config.py` 注入 CSS。

**方案**：将 CSS 和主题色全部集中到 `config/theme.py`，UI 组件只从 `config/` 引用——因为 `config/` 是底层共享模块。

```python
# ui/components.py  —— 只依赖 config/ 和 streamlit
from config.theme import COLORS, GLOBAL_CSS, MOBILE_CSS

class UI:
    @staticmethod
    def inject_css():
        st.markdown(GLOBAL_CSS + MOBILE_CSS, unsafe_allow_html=True)
    ...
```

### 3.6 Page 层模式

每个页面文件 ≤ 120 行，遵循统一模式：

```python
# pages/overview.py
"""总览页面"""
import streamlit as st
from services.overview import OverviewService
from ui.components import UI

def render():
    UI.inject_css()
    UI.header("总览", "资产概览与趋势")

    # 1. 从 Session State 获取共享数据（不重新请求 API）
    usd_rmb = st.session_state.usd_rmb
    hkd_rmb = st.session_state.hkd_rmb

    # 2. 调用 Service（自带 @st.cache_data 缓存）
    metrics = OverviewService.get_metrics(usd_rmb, hkd_rmb)

    # 3. 渲染
    UI.metric_row([
        ("总资产", f"¥{metrics['total_rmb']:,.0f}"),
        ...
    ])

    # 4. 图表（按需加载）
    trend = OverviewService.get_trend()
    if trend is not None:
        _render_trend_chart(trend)

def _render_trend_chart(df):
    ...
```

**模式要点**：
1. **汇率从 Session State 读**，不调 API —— 保证跨页面一致性
2. **Service 方法自带缓存**，页面层不需要管缓存逻辑
3. **页面内状态用 `page_{name}_{field}` 命名**，页面切换时自动清理
4. **写操作后调用 `on_transaction_added()`** 清除受影响的缓存

---

## 四、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 重构期间引入回归 Bug | 高 | 中 | 每个 Phase 完成后运行应用验证 |
| 数据库 Schema 变更导致数据丢失 | 中 | 高 | 不做破坏性 Schema 变更，只加索引/删空表 |
| 投资组合 Tab 仍然不响应 | 中 | 高 | Phase 7 专项修复 + 利用 Session State 管理 Tab 状态 |
| 拆分 service 后导入路径大量变更 | 必然 | 低 | 一次性全量替换，不保留旧路径兼容层 |
| Session State 键名冲突 | 低 | 中 | 严格执行 `page_{name}_{field}` 命名规范 |
| `@st.cache_data` 返回脏数据 | 中 | 中 | 写操作后主动 `.clear()`，TTL 不超过 10 分钟 |
| 多设备并发写 SQLite | 中 | 高 | 启用 WAL 模式 + `@st.cache_resource` 单连接 |

---

## 五、验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 零死文件 | `git ls-files` 中无 v1 遗留 |
| 2 | 每个常量只定义一次 | `grep -r OPTION_ACTIONS` 只出现 1 处定义 |
| 3 | `dict_to_transaction` 只有 1 份 | `grep -rn dict_to_transaction` 验证 |
| 4 | 所有模块 < 300 行 | `wc -l` 验证 |
| 5 | `services/` 不 import streamlit（仅 `@st.cache_data` 除外） | `grep` 验证：只有装饰器引用 |
| 6 | `ui/` 不 import `pages/` | 依赖检查 |
| 7 | `db/` 不 import `services/` | 依赖检查 |
| 8 | 8 个页面全部正常渲染 | 浏览器逐页点击验证 |
| 9 | 投资组合 3 个 Tab 全部可交互 | 点击切换、数据加载、图表渲染 |
| 10 | `py_compile` 全部通过 | 批量编译检查 |
| 11 | Mock 数据符合新 Schema | `seed_mock_data.py` 生成的数据全部带正确的 category 枚举值 |
| 12 | `st.session_state.rates` 跨页面持久 | 切换 3 个不同页面后检查汇率值不变 |
| 13 | Service 缓存生效 | 同一页面连续 2 次加载，第 2 次 < 50ms |
| 14 | 新增交易后数据更新 | 添加一笔交易后，总览和交易日志页面立即反映 |
| 15 | category 隔离彻底 | 收支页千万不包含 BUY/SELL 操作，投资页千万不包含 INCOME/EXPENSE |
| 16 | 数据库 CHECK 约束生效 | 尝试写入非法 action/category 时 SQLite 报错 |

---

## 六、文件删减汇总

| 状态 | 数量 | 行数 |
|------|------|------|
| 删除 | 20 个文件/目录 | ~4,700 行代码 + ~1,200 行文档 |
| 新建 | ~40 个 .py 文件（含 __init__.py） | ~3,500 行 |
| 最终 | ~45 个文件 | ~3,500 行 |

重构后**代码量从 ~9,000 行降至 ~3,500 行**（减少约 60%），功能完全保留且新增预留接口。

---

## 七、阶段执行顺序

```
Phase 0  删除死文件                        ▓░░░░░░░  (10 min)
Phase 1  抽取 config/ + 分类隔离常量      ▓▓░░░░░░  (40 min)  ← SSOT
Phase 2  统一 models/                     ▓▓▓░░░░░  (30 min)
Phase 3  拆分 db/ + Schema CHECK 约束     ▓▓▓▓░░░░  (40 min)
Phase 4  拆分 services/ (域隔离)          ▓▓▓▓▓▓░░  (2 hrs)   ← 核心
Phase 5  重整 ui/                         ▓▓▓▓▓▓▓░  (30 min)
Phase 6  重写 pages/                      ▓▓▓▓▓▓▓▓  (1 hr)
Phase 7  修复 portfolio + Mock数据 + 验证   ▓▓▓▓▓▓▓▓  (1 hr)
```

> 是否开始执行？请确认后逐 Phase 推进。
