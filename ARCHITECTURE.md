## 🏗️ 项目架构重构说明

### 📁 目录结构

```
option-go/
├── src/
│   ├── __init__.py                 # 向后兼容层，导出所有公共 API
│   │
│   ├── models/                    # 📊 数据模型层（核心数据定义）
│   │   ├── __init__.py
│   │   ├── transaction.py        # 交易模型 + 枚举
│   │   ├── campaign.py           # 策略周期模型
│   │   └── account.py            # 账户和账户分类模型
│   │
│   ├── options/                   # 🎯 期权计算模块
│   │   ├── __init__.py
│   │   ├── calculator.py         # 基础期权计算（仓位、盈亏、权利金）
│   │   └── wheel_strategy.py     # 车轮策略专用计算器
│   │
│   ├── portfolio/                 # 💼 组合分析模块
│   │   ├── __init__.py
│   │   ├── calculator.py         # 组合汇总计算
│   │   └── analyzer.py           # 组合风险/表现分析
│   │
│   ├── visualization/             # 📈 可视化模块
│   │   ├── __init__.py
│   │   ├── charts.py             # Plotly 图表函数
│   │   └── dashboards.py         # Streamlit 仪表板组件
│   │
│   ├── database/                  # 🗄️ 数据库模块
│   │   └── __init__.py           # (待迁移原有的 database.py)
│   │
│   ├── trading/                   # 💱 交易处理模块
│   │   └── __init__.py           # (待迁移交易逻辑)
│   │
│   └── integrations/              # 🔗 第三方集成
│       ├── __init__.py
│       └── telegram_handler.py   # Telegram Bot 处理器
│
├── app.py                          # Streamlit 前端 v1
├── app_v2.py                       # Streamlit 前端 v2
├── requirements.txt                # 依赖
├── README.md
└── ARCHITECTURE.md                 # 本文件
```

---

### 🎯 模块职责详解

#### 📊 **models/** - 数据模型层
**职责**: 定义所有数据结构，不包含业务逻辑

**包含**:
- `Transaction` - 统一交易模型
- `TransactionType`, `OptionSubtype`, `StockSubtype` - 枚举
- `Campaign` - 策略周期（一个完整的车轮周期）
- `Account`, `AccountCategory` - 账户模型

**使用场景**:
```python
from src.models import Transaction, TransactionType

tx = Transaction(
    type=TransactionType.OPTION,
    subtype="sell_put",
    date="2026-01-01",
    amount=-100,
    symbol="AAPL",
    quantity=1
)
```

---

#### 🎯 **options/** - 期权计算模块
**职责**: 所有期权相关的数学计算

**包含**:
1. **calculator.py** - `OptionCalculator`
   - `calculate_option_positions(symbol)` - 期权仓位
   - `calculate_option_pnl(symbol)` - 期权盈亏
   - `get_open_positions(symbol)` - 未平仓头寸
   - `get_premiums_summary()` - 权利金统计

2. **wheel_strategy.py** - `WheelStrategyCalculator`
   - `calculate_adjusted_cost_basis(symbol)` - 调整成本基准 ⭐
   - `calculate_unrealized_pnl(symbol, price)` - 浮动盈亏
   - `calculate_campaign_summary(symbol, price)` - 策略汇总
   - `calculate_breakeven_weeks(symbol, premium)` - 回本计算
   - `get_wheel_cycle_info(symbol)` - 周期阶段

**关键概念**:

**金额符号约定**（所有模块统一）:
```
amount > 0 → 支出/成本/买入（如：买入100股花了10000）
amount < 0 → 收入/收益/卖出（如：卖出100股收了11000，记为-11000）
```

**调整成本基准公式** (车轮策略核心):
```
adjusted_cost_per_share = (股票购入成本 - 期权收入 + 手续费) / 当前持股数

示例：
- 买入100股 @ $100 → cost_basis = 10000
- 收取权利金 → 减少成本基准
- 结果：adjusted_cost = (10000 - premium_income + fees) / 100
```

**使用场景**:
```python
from src.options import WheelStrategyCalculator

calc = WheelStrategyCalculator(transactions)

# 获取调整成本（核心）
basis = calc.calculate_adjusted_cost_basis("AAPL")
print(f"持仓: {basis['current_shares']}股")
print(f"调整成本: ${basis['adjusted_cost']:.2f}") 
print(f"成本总额: ${basis['cost_basis']:,.2f}")

# 计算浮动盈亏
unrealized = calc.calculate_unrealized_pnl("AAPL", current_price=185)
print(f"当前浮动盈亏: ${unrealized['unrealized_pnl']:,.2f}")

# 回本机制
breakeven = calc.calculate_breakeven_weeks("AAPL", avg_weekly_premium=2.5)
print(breakeven['message'])  # 例：以每周 $2.50 权利金计算，还需 8.0 周回本
```

---

#### 💼 **portfolio/** - 组合分析模块
**职责**: 多个持仓的综合分析

**包含**:
1. **calculator.py** - `PortfolioCalculator`
   - `get_portfolio_summary(prices)` - 全组合汇总
   - `get_asset_allocation(prices)` - 资产配比
   - `get_total_market_value(prices)` - 总市值
   - `get_all_positions()` - 所有仓位信息

2. **analyzer.py** - `PortfolioAnalyzer`
   - `get_symbol_statistics(symbol, price)` - 单个持仓统计
   - `get_premium_efficiency()` - 权利金效率 ⭐
   - `get_diversification_analysis(prices)` - 多样化分析
   - `get_risk_metrics(prices)` - 风险指标
   - `get_performance_summary(prices)` - 完整表现

**使用场景**:
```python
from src.portfolio import PortfolioCalculator, PortfolioAnalyzer

calc = PortfolioCalculator(transactions)
analyzer = PortfolioAnalyzer(transactions)

# 组合汇总
summary = calc.get_portfolio_summary(
    prices={"AAPL": 185, "SLV": 28.5}
)
print(f"总持仓: ${summary['total']}")  # 🎯 重点提示，需要补充

# 权利金效率（重要指标）
efficiency = analyzer.get_premium_efficiency()
print(f"{efficiency['message']}")  # 例：每投入 $100 成本，已收 $12.50 权利金

# 风险分析
risk = analyzer.get_risk_metrics(prices)
print(f"风险等级: {risk['risk_level']}")
```

---

#### 📈 **visualization/** - 可视化模块
**职责**: 所有图表和仪表板显示

**包含**:
1. **charts.py** - Plotly 图表函数
   - `plot_cost_basis_over_time()` - 成本基准时间线
   - `plot_pnl_heatmap()` - P&L 热力图
   - `plot_portfolio_allocation()` - 资产配置饼图
   - `plot_campaign_pnl()` - 策略盈亏分解
   - `plot_breakeven_progress()` - 回本进度条
   - `plot_premium_history()` - 权利金历史
   - `plot_combined_pnl()` - 综合盈亏

2. **dashboards.py** - `PortfolioDashboard`
   - `render_summary_metrics()` - 关键指标卡
   - `render_allocation()` - 资产配置图
   - `render_holdings_table()` - 持仓表格
   - `render_pnl_breakdown()` - 盈亏分解
   - `render_analysis()` - 分析报告
   - `render_full_dashboard()` - 完整仪表板

**使用场景**:
```python
from src.visualization import PortfolioDashboard

dashboard = PortfolioDashboard(
    transactions=transactions,
    prices={"AAPL": 185}
)

dashboard.render_full_dashboard()  # Streamlit 应用中直接渲染
```

---

#### 🗄️ **database/** - 数据库模块
**职责**: 数据库连接、CRUD 操作、持久化

> 🔄 **待迁移**: 原有的 `database.py` 和 `database_v2.py` 的内容

计划函数：
- `init_database()` - 初始化表结构
- `add_transaction(tx)` - 添加交易
- `get_transactions(symbol, date_range)` - 查询交易
- `update_daily_price(symbol, date, price)` - 更新股价

---

#### 💱 **trading/** - 交易处理模块
**职责**: 交易验证、处理、自然语言解析

> 🔄 **待迁移/扩展**: Telegram 消息解析等交易逻辑

计划内容：
- 交易验证（金额、数量、日期等）
- 自然语言解析（"买入100股AAPL @180"）
- 交易批处理

---

#### 🔗 **integrations/** - 集成模块
**职责**: 第三方服务（Telegram, 数据源等）

**包含**:
- `TelegramHandler` - Telegram Bot 消息处理
  - `process_message(msg)` - 处理消息
  - `parse_natural_language()` - 自然语言解析
  - 各种命令处理

---

### 🔄 迁移指南（从旧代码到新代码）

#### **旧代码导入**:
```python
from src.calculator import WheelCalculator, PortfolioCalculator
from src.models import Transaction
```

#### **新代码导入**:
```python
# ✅ 推荐方式1: 从具体模块导入
from src.options import WheelStrategyCalculator as WheelCalculator
from src.portfolio import PortfolioCalculator
from src.models import Transaction

# ✅ 推荐方式2: 从向后兼容层导入（过渡期）
from src import WheelCalculator, Transaction  # 自动转向新位置
```

**关键变化**:
- `WheelCalculator` → `WheelStrategyCalculator`（模块位置变了，但 `src/__init__.py` 有别名）
- `src.calculator` → `src.options.wheel_strategy`
- 所有函数、参数名称和返回值结构保持不变 ✅

---

### 🚀 前端架构 (Streamlit)

#### **app.py** (v1)
- 使用 `src.database.get_transactions()`
- 使用 `WheelCalculator` 计算
- 自定义 HTML/CSS 显示

#### **app_v2.py** (v2 - 推荐)
- 更现代的 UI
- 使用 `PortfolioDashboard` 组件
- 支持多账户、多币种
- 数据快照和历史记录

#### **推荐用法**:
```python
# app_v2.py 中
import streamlit as st
from src.visualization import PortfolioDashboard

transactions = get_transactions()  # 从数据库加载
prices = fetch_current_prices()   # 实时行情

dashboard = PortfolioDashboard(transactions, prices)
dashboard.render_full_dashboard()
```

---

### 💡 关键概念速查表

| 概念 | 位置 | 说明 |
|------|------|------|
| **Transaction** | `models.transaction` | 单笔交易记录 |
| **Campaign** | `models.campaign` | 一个诸如买入-卖put-接盘-被买走的完整周期 |
| **OptionCalculator** | `options.calculator` | 期权仓位和盈亏计算 |
| **WheelStrategyCalculator** | `options.wheel_strategy` | 车轮策略专用（核心！） |
| **adjusted_cost_basis** | `WheelStrategyCalculator` | 调整成本基准（最重要的指标） |
| **PortfolioCalculator** | `portfolio.calculator` | 多持仓汇总 |
| **PortfolioAnalyzer** | `portfolio.analyzer` | 风险和表现分析 |
| **PortfolioDashboard** | `visualization.dashboards` | Streamlit 仪表板 |

---

### 🧪 测试验证

已验证的修复 (见 `test_calculator_fixes.py`):
- ✅ 期权盈亏计算
- ✅ 调整成本基准计算  
- ✅ 已实现盈亏计算
- ✅ 未实现盈亏计算

运行测试:
```bash
python test_calculator_fixes.py
```

---

### 📋 下一步行动

1. ✅ 完成 models 分离
2. ✅ 完成 options 模块
3. ✅ 完成 portfolio 模块
4. ✅ 完成 visualization 模块
5. ⏳ 迁移 database 模块（原 database.py）
6. ⏳ 创建 trading 模块（交易验证逻辑）
7. ⏳ 更新 app.py 和 app_v2.py 的导入
8. ⏳ 编写完整文档和使用示例

---

### 📞 常见问题

**Q: 我的旧 app.py 如何继续工作?**
A: `src/__init__.py` 提供了向后兼容层。但建议升级到新的导入模式。

**Q: 为什么要分离就器?**
A: 
- 🎯 单一职责：每个模块只做一件事
- 🔄 易于测试：可以独立测试每个模块
- 📦 易于复用：其他项目可以直接导入子模块
- 🛠️ 易于维护：代码组织更清晰

**Q: 性能会影响吗?**
A: 不会，Python 导入优化很好，多一层导入不会有性能问题。

---

### 📚 相关文件

- [models/transaction.py](src/models/transaction.py) - 交易模型详解
- [options/calculator.py](src/options/calculator.py) - 期权计算详解
- [portfolio/analyzer.py](src/portfolio/analyzer.py) - 分析方法详解
