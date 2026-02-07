# 架构重整技术方案

> 状态：**已批准** ✅  
> 日期：2026-02-07  
> 批准日期：2026-02-07

---

## 一、问题诊断

### 1.1 `models/` 为什么没有接入？

Phase 2 创建了 `models/` 目录（Transaction/Account/Snapshot dataclass + converters），但**零处活跃代码引用它**。根因：

| 层 | 实际数据流 | 说明 |
|----|-----------|------|
| `db/` | 返回 `sqlite3.Row`（行为类似 dict） | — |
| `services/` | dict → `pd.DataFrame` | **直接跳过 dataclass**，一步到 DataFrame |
| `pages/` | 操作 DataFrame + 渲染 | — |
| 计算器（`src/portfolio`, `src/options`） | 使用**旧版**  `src.models.Transaction` | 字段不同：旧模型用 type/subtype/amount，新模型用 action/category/price×quantity |

结论：`services/` 层从 dict 直接到 DataFrame，中间没有 dataclass 的插入点。同时计算器仍绑定旧模型，新 models/ 没有消费者。

### 1.2 需要接入吗？

**建议：当前阶段不接入，理由如下：**

| 接入 models/ 的收益 | 成本 |
|---------------------|------|
| IDE 自动补全、类型安全 | 每条记录多一次 dict → dataclass 转换 |
| `tx.is_option` 等属性方法 | 但 services 实际用 `df[df.action.isin(...)]` 过滤，不需要逐条判断 |
| 统一 `dict_to_transaction` | 但唯一的消费者（计算器）还绑定旧模型，换了也不能删旧版 |

**真正要解决的是**：消灭 `src/` 旧层的传递依赖（`src.models` → `src.options` → `src.portfolio` → `src.finance_engine`），而不是强行把新 models/ 插入 DataFrame 的流水线里。

**最终决定**：
- `models/` 目录**暂时删除**（265 行，零引用，保持代码库干净）
- 等 `src/options/WheelStrategyCalculator` 和 `src/portfolio/PortfolioCalculator` 被重写进 `services/` 后，`src.models.Transaction` 自然消失，届时再评估是否需要 dataclass 层
- 如果未来需要 dataclass（比如引入 API server / Pydantic），在 `models/` 重新创建即可，成本很低

---

## 二、目标架构

### 2.1 目录结构

```
option-go/
├── app.py                          # 入口（路由 + session_state 初始化）
│
├── config/                         # 纯配置（不变）
│   ├── constants.py
│   ├── labels.py
│   └── theme.py
│
├── db/                             # 数据访问（不变）
│   ├── connection.py
│   ├── transactions.py
│   ├── accounts.py
│   ├── snapshots.py
│   ├── yearly.py
│   └── exchange_rates.py
│
├── utils/                          # 跨域工具函数（新建）
│   ├── __init__.py
│   └── currency.py                 #   to_rmb(), fetch_rates()
│
├── ui/                             # UI 原子组件 + 图表（不变）
│   ├── __init__.py
│   ├── components.py
│   └── charts.py
│
├── api/                            # 外部数据源（不变）
│   ├── exchange_rates.py
│   ├── stock_data.py
│   └── stock_names.py
│
├── services/                       # 按业务域隔离
│   ├── assets/                     #   域1: 资产追踪
│   │   ├── __init__.py
│   │   ├── overview.py             #     OverviewService
│   │   ├── snapshot.py             #     SnapshotService
│   │   └── yearly.py              #     YearlyService
│   ├── accounting/                 #   域2: 日常记账
│   │   ├── __init__.py
│   │   └── expense.py             #     ExpenseService
│   ├── investing/                  #   域3: 投资监控
│   │   ├── __init__.py
│   │   ├── trading.py             #     TradingService
│   │   ├── portfolio/             #     PortfolioService + mixins
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   ├── holdings.py
│   │   │   └── options.py
│   │   └── strategies/            #     策略引擎
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── wheel/
│   │           ├── __init__.py
│   │           ├── service.py
│   │           ├── calculator.py
│   │           └── charts.py
│   │   │   ├── _helpers.py         #     portfolio 内部辅助（cumulative_deposits 等）
│
├── pages/                          # 按业务域隔离
│   ├── assets/                     #   域1: 资产追踪
│   │   ├── __init__.py
│   │   ├── overview.py
│   │   ├── snapshots.py
│   │   └── yearly.py
│   ├── accounting/                 #   域2: 日常记账
│   │   ├── __init__.py
│   │   └── expense.py
│   ├── investing/                  #   域3: 投资监控
│   │   ├── __init__.py
│   │   ├── trading.py
│   │   ├── wheel.py
│   │   └── portfolio/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── tab_overview.py
│   │       ├── tab_holdings.py
│   │       └── tab_options.py
│   └── settings.py                #   系统设置（单文件）
│
├── scripts/
│   └── seed_mock_data.py
│
└── 删除 ──────────────────────────
    ├── frontend/                   # 全删
    ├── src/                        # 全删
    ├── models/                     # 暂删（零引用）
    ├── tests/                      # 空目录，删
    ├── app_v2.py                   # 重命名为 app.py
    └── UPDATES.md                  # 过渡文档，删
```

### 2.2 依赖方向（严格单向）

```
app.py
  ↓
pages/          →  services/  →  db/
  ↓                   ↓
  ui/              config/
  ↓                api/
config/            utils/
utils/
```

禁止：
- `db/` → `services/`
- `services/` → `pages/`
- `ui/` → `services/` 或 `pages/`
- 任何层 → `src/` 或 `frontend/`（这两个将被删除）

---

## 三、变更清单

### Step 1：迁移旧层残留函数（消灭 `frontend/` 依赖）

| 源 | 函数 | 目标 | 调用方 |
|----|------|------|--------|
| `frontend/helpers.py` | `fetch_exchange_rates()` | `utils/currency.py` | `app.py`, `pages/assets/snapshots.py` |
| `frontend/helpers.py` | `to_rmb()` | `utils/currency.py` | `pages/assets/snapshots.py` |
| `frontend/helpers.py` | `dict_to_transaction()` | 内联到调用处 | `pages/investing/portfolio/tab_options.py`（见 Step 2） |
| `frontend/helpers.py` | `plotly_layout()` | 已存在于 `ui/charts.py` | 无需迁移 |
| `frontend/helpers.py` | `metric_row()` | 已存在于 `ui/components.py` | 无需迁移 |
| `frontend/helpers.py` | `stock_label()` | 直接调 `api.stock_names.get_stock_label()` | 无需包装 |

`utils/currency.py` 内容（~30 行）：

```python
"""货币工具函数"""
import streamlit as st
from typing import Dict
from api.exchange_rates import get_exchange_rates as _api_get_rates

@st.cache_data(ttl=3600)
def fetch_rates() -> Dict:
    """获取汇率（缓存 1 小时）"""
    raw = _api_get_rates()
    return {
        "USD": {"usd": 1.0, "rmb": raw["USD"]["cny"]},
        "CNY": {"usd": raw["CNY"]["usd"], "rmb": 1.0},
        "HKD": {"usd": raw["HKD"]["usd"], "rmb": raw["HKD"]["cny"]},
    }

def to_rmb(amount: float, currency: str, rates: Dict) -> float:
    """金额 → 人民币"""
    if currency == "CNY":
        return amount
    return amount * rates.get(currency, {}).get("rmb", 1.0)
```

### Step 2：消灭 `src/` 残留依赖

当前状态：

| 旧模块 | 被谁引用 | 引用的符号 | 解法 |
|-------|---------|-----------|------|
| `src.options.WheelStrategyCalculator` | `services/investing/portfolio/options.py` | 计算器类 | `services/investing/strategies/wheel/calculator.py` 已有 `WheelCalculator` 新类，改引用 |
| `src.options.WheelStrategyCalculator` | `services/investing/strategies/wheel/service.py` | 同上 | 同上 |
| `src.options.WheelStrategyCalculator` | `pages/investing/portfolio/tab_options.py` | 同上 | 同上 |
| `src.finance_engine.dict_to_transaction` | `services/investing/strategies/wheel/service.py` | 旧 dict→Transaction 转换 | 内联：直接在 service 中构造旧 Transaction |
| `src.finance_engine.dict_to_transaction` | `services/investing/portfolio/service.py` | 同上 | 同上 |
| `src.portfolio.PortfolioCalculator` | `services/investing/portfolio/service.py` | 组合计算器 | 将 PortfolioCalculator 搬入 `services/investing/portfolio/calculator.py`，去掉旧模型依赖 |

> **注意**：`src.finance_engine.dict_to_transaction` 内部将 dict 转为**旧版** `src.models.Transaction`（有 type/subtype/amount 字段），这是给 `PortfolioCalculator` 用的。当 PortfolioCalculator 被重写后，这条依赖链自然消失。

### Step 3：按业务域重组 `pages/` 和 `services/`

纯文件移动 + import 路径更新：

| 原路径 | 新路径 | 业务域 |
|--------|--------|--------|
| `pages/overview.py` | `pages/assets/overview.py` | 资产追踪 |
| `pages/snapshots.py` | `pages/assets/snapshots.py` | 资产追踪 |
| `pages/yearly.py` | `pages/assets/yearly.py` | 资产追踪 |
| `pages/expense.py` | `pages/accounting/expense.py` | 日常记账 |
| `pages/trading.py` | `pages/investing/trading.py` | 投资监控 |
| `pages/wheel.py` | `pages/investing/wheel.py` | 投资监控 |
| `pages/portfolio/*` | `pages/investing/portfolio/*` | 投资监控 |
| `pages/settings.py` | `pages/settings.py` | 系统（不变） |
| `services/overview.py` | `services/assets/overview.py` | 资产追踪 |
| `services/snapshot.py` | `services/assets/snapshot.py` | 资产追踪 |
| `services/yearly.py` | `services/assets/yearly.py` | 资产追踪 |
| `services/expense.py` | `services/accounting/expense.py` | 日常记账 |
| `services/trading.py` | `services/investing/trading.py` | 投资监控 |
| `services/portfolio/*` | `services/investing/portfolio/*` | 投资监控 |
| `services/strategies/*` | `services/investing/strategies/*` | 投资监控 |
| `services/_helpers.py` | `services/investing/portfolio/_helpers.py` | 投资监控（仅 portfolio 引用） |

### Step 4：更新 `app.py` 路由

```python
from utils.currency import fetch_rates     # 替代 frontend.helpers
from pages.assets import overview, snapshots, yearly
from pages.accounting import expense
from pages.investing import trading, wheel, portfolio
from pages import settings
```

### Step 5：删除旧层

```bash
rm -rf frontend/ src/ models/ tests/ UPDATES.md
mv app_v2.py app.py
```

---

## 四、不做什么

| 项目 | 理由 |
|------|------|
| 接入 `models/` dataclass | 当前 dict→DataFrame 流水线高效且稳定，dataclass 无消费者 |
| 重写 PortfolioCalculator | 该计算器 ~400 行，逻辑复杂（持仓跟踪/P&L/成本基准），风险高。本次只搬位置，不改逻辑。**→ 列为后续重构任务（方案 B：重写为 DataFrame-native，消除旧 Transaction 依赖）** |
| 拆分 `db/transactions.py` | 它通过 `category_in` 参数在查询层就实现了域隔离，无需拆分 |
| 引入 logging | 属于代码质量改进，不在本次范围（可后续 ticket） |
| 增加错误处理 | 同上 |

---

## 五、验证标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `frontend/` 和 `src/` 目录不存在 | `ls` |
| 2 | `models/` 目录不存在 | `ls` |
| 3 | 零处 `from frontend` 或 `from src` import | `grep -r` |
| 4 | pages/ 按三域分文件夹 | 目录结构检查 |
| 5 | services/ 按三域分文件夹 | 目录结构检查 |
| 6 | `utils/currency.py` 存在且导出 `fetch_rates`, `to_rmb` | import 测试 |
| 7 | `py_compile` 全部通过 | 批量编译 |
| 8 | Phase 4-7 回归测试通过 | 运行 test_phase*.py |
| 9 | `streamlit run app.py` 8 个页面正常渲染 | 浏览器验证 |
| 10 | 依赖方向无违规 | `grep` 交叉检查 |

---

## 六、执行顺序

```
Step 1  创建 utils/ + 迁移函数         15 min    低风险
Step 2  消灭 src/ 残留依赖              1 hr     中风险（计算器搬运）
Step 3  按域重组 pages/ + services/     30 min    低风险（纯移动）
Step 4  更新 app.py 路由               10 min    低风险
Step 5  删除旧层 + 回归测试             15 min    验证
```

预计总耗时：~2.5 小时

---

## 七、决策记录

| # | 问题 | 决定 | 理由 |
|---|------|------|------|
| 1 | `app_v2.py` → `app.py` 重命名 | ✅ 执行 | 旧 `app.py` 已在 Phase 0 删除 |
| 2 | PortfolioCalculator 搬运策略 | ✅ **方案 A**（原样搬） | 先完成架构清理，**重写为 DataFrame-native 列为后续重构任务** |
| 3 | `_helpers.py` 位置 | ✅ 移入 `services/investing/portfolio/_helpers.py` | 3 个函数只被 portfolio/ 引用，不是“跨域”，应下沉到 portfolio 内部 |

---

## 八、后续重构任务（Backlog）

| # | 任务 | 描述 | 预计工作量 |
|---|------|------|------------|
| B-1 | PortfolioCalculator 重写为 DataFrame-native | 消除旧 `src.models.Transaction` 依赖，让 calculator 直接处理 dict/DataFrame，与其他 Service 风格一致 | ~1 天 |
| B-2 | 评估是否需要 dataclass 层 | 等 B-1 完成后，重新评估 models/ 目录的必要性 | 半天 |
