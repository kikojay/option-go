# Wealth Tracker — 个人财富追踪器

基于 Streamlit 的个人财富管理工具，覆盖 **资产总览、月度快照、年度汇总、收支管理、美股投资组合、期权车轮策略** 等场景。

复古金融报告风格 UI，支持多币种（USD / CNY / HKD）自动汇率换算，适合部署到 VPS 作为 PWA 使用。

---

## 技术栈

| 组件 | 选型 |
|------|------|
| 前端框架 | Streamlit 1.28+ |
| 数据可视化 | Plotly |
| 数据库 | SQLite（标准库 sqlite3） |
| 行情数据 | yfinance |
| 汇率数据 | 自建 API 缓存层 |
| Python | 3.11+ |

---

## 项目架构

按业务域隔离的四层架构，单向依赖：**pages → services → db**，工具/UI 横切。

```
app.py                           # 应用入口 — 路由 + 侧边栏导航
│
├── config/                      # 纯配置（常量/标签/主题）
│   ├── constants.py
│   ├── labels.py
│   └── theme.py
│
├── db/                          # 数据访问层 — 纯 CRUD
│   ├── connection.py            #   连接管理 + Schema 初始化
│   ├── transactions.py          #   交易记录（自动 category 推断）
│   ├── accounts.py              #   账户管理
│   ├── snapshots.py             #   月度快照
│   ├── yearly.py                #   年度汇总
│   └── exchange_rates.py        #   汇率缓存
│
├── utils/                       # 跨域工具函数
│   └── currency.py              #   汇率获取 + 金额换算
│
├── ui/                          # UI 原子组件 + 图表
│   ├── components.py            #   卡片/表格/指标行等
│   └── charts.py                #   Plotly 图表封装
│
├── api/                         # 外部数据接口
│   ├── exchange_rates.py        #   汇率 API + 本地缓存
│   ├── stock_data.py            #   股票行情（yfinance）
│   └── stock_names.py           #   股票中文名映射
│
├── services/                    # 业务逻辑层 — 按域隔离
│   ├── assets/                  #   域1: 资产追踪
│   │   ├── overview.py          #     OverviewService
│   │   ├── snapshot.py          #     SnapshotService
│   │   └── yearly.py            #     YearlyService
│   ├── accounting/              #   域2: 日常记账
│   │   └── expense.py           #     ExpenseService
│   ├── investing/               #   域3: 投资监控
│   │   ├── trading.py           #     TradingService
│   │   ├── portfolio/           #     PortfolioService + mixins
│   │   │   ├── service.py
│   │   │   ├── holdings.py
│   │   │   ├── options.py
│   │   │   └── _helpers.py
│   │   └── strategies/          #     策略引擎（可扩展）
│   │       ├── base.py
│   │       └── wheel/           #       车轮策略
│   │           ├── service.py
│   │           ├── calculator.py
│   │           └── charts.py
│   └── _legacy/                 #   旧版计算器兼容层（待重构）
│       ├── models.py
│       ├── option_calc.py
│       ├── wheel_calc.py
│       ├── portfolio_calc.py
│       └── converters.py
│
├── pages/                       # 视图层 — 按域隔离
│   ├── assets/                  #   域1: 资产追踪
│   │   ├── overview.py          #     总览
│   │   ├── snapshots.py         #     月度快照
│   │   └── yearly.py            #     年度汇总
│   ├── accounting/              #   域2: 日常记账
│   │   └── expense.py           #     收支管理
│   ├── investing/               #   域3: 投资监控
│   │   ├── trading.py           #     交易日志
│   │   ├── wheel.py             #     期权车轮
│   │   └── portfolio/           #     投资组合（4 Tab）
│   │       ├── main.py
│   │       ├── tab_overview.py
│   │       ├── tab_holdings.py
│   │       └── tab_options.py
│   └── settings.py              #   系统设置
│
├── scripts/
│   └── seed_mock_data.py        # 模拟数据生成
│
└── data/
    ├── wealth.db                # SQLite 数据库（自动创建）
    └── cache/                   # API 缓存文件
```

### 分层职责

| 层 | 职责 | 规则 |
|---|------|------|
| **数据层** `db/` | 纯 CRUD，返回 dict / list | 不含业务逻辑 |
| **服务层** `services/` | 业务计算、数据聚合、缓存 | 不依赖 UI，按业务域隔离 |
| **UI 组件** `ui/` | 卡片、表格、图表等原子渲染 | 只做渲染，不做计算 |
| **视图层** `pages/` | 页面编排：Service → UI 渲染 | 不直接碰 DB |
| **工具层** `utils/` | 跨域通用函数（汇率等） | 纯函数，无 side effect |

### 依赖方向（严格单向）

```
app.py → pages/ → services/ → db/
                       ↓
                    config/ / api/ / utils/
         pages/ → ui/
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/kikojay/option-go.git
cd option-go
```

### 2. 创建环境 & 安装依赖

```bash
# conda 方式（推荐）
conda create -n ai python=3.11 -y
conda activate ai
pip install -r requirements.txt

# 或 venv 方式
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 生成模拟数据（可选）

```bash
python scripts/seed_mock_data.py --reset
```

### 4. 启动应用

```bash
streamlit run app.py --server.port 8501
```

浏览器打开 `http://localhost:8501` 即可使用。

数据库 `data/wealth.db` 会在首次启动时自动创建。

### 5. VPS 部署（可选）

```bash
# 后台运行 + 无头模式
nohup streamlit run app.py \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false \
  > /dev/null 2>&1 &
```

建议配合 Nginx 反向代理 + HTTPS。移动端 PWA 访问时，UI 会自动切换为流式单列布局。

---

## 测试与 Shadow 数据库

- prod: `data/wealth.db`
- shadow: `data/wealth_test.db`
- 测试默认只操作 shadow。

一键从 prod 拷贝到 shadow：

```bash
python -c "from db.connection import sync_shadow_from_prod; sync_shadow_from_prod()"
```

---

## 功能模块

| 页面 | 说明 |
|------|------|
| 总览 | 净资产卡片、资产分类饼图、趋势折线图 |
| 月度快照 | 多账户资产快照，自动/手动记录，支持历史回溯 |
| 年度汇总 | 税前税后收入、社保个税、投资收益对比 |
| 收支管理 | 按月/按类别统计收支，储蓄率，趋势图 |
| 投资组合 | 持仓明细（实时行情）、资金流水、TWR 收益率曲线 |
| 交易日志 | 交易记录 CRUD，买卖/权利金统计 |
| 期权车轮 | Wheel 策略分析：成本基准、回本预测、热力图、收益分布 |
| 设置 | 数据备份、数据库信息 |

---

## 多币种支持

- 自动获取 USD/CNY、HKD/CNY 实时汇率
- 所有金额支持 USD ↔ CNY 双币显示
- 汇率缓存于 `data/cache/exchange_rates.json`，避免频繁请求

---

## License

MIT
