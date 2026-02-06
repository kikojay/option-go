# Option Wheel Tracker - Personal Finance & Investment Management

## 版本 2.0 - 完整重构

### 模块 1：个人资产管理

#### A: 总览 Overview
- 资产大类：A股、美股、公积金、应收账款、Kraken（加密）、期权、现金、其他
- 多币种汇率自动获取（RMB/USD/HKD）
- 总资产数值、增长曲线、占比饼图

#### B: 月度快照 Snapshots
- 定期记录资产快照
- 历史曲线
- 一键生成新快照

#### C: 年度汇总 Yearly Summary
- 收入/支出/税务追踪
- 税前 vs 税后增长对比

#### D: 支出追踪 Expense Tracker
- 逐笔记录
- 分类统计
- 月度汇总

### 模块 2：投资追踪

#### A: 持仓 Portfolio
- 多类别支持
- 自动计算盈亏
- CSV 导入

#### B: 交易日志 Trading Log
- 完整交易记录
- 批量导入
- 策略关联

#### C: 期权车轮 Options Wheel
- 策略链路追踪
- 累计权利金
- 回本计算

---

## 数据模型与口径

### 资产模型
```sql
assets (
    id, type, name, currency, amount, 
    created_at, updated_at
)
```

### 交易模型
```sql
transactions (
    id, date, symbol, action, quantity, price,
    fees, currency, account, category, strategy_id,
    created_at
)
```

### 快照模型
```sql
snapshots (
    id, date, total_assets, data_json,
    is_latest, created_at
)
```

### 计算口径

| 指标 | 公式 |
|------|------|
| Cost Basis | 累计买入成本 - 累计卖出收入 |
| Market Value | 持仓数量 × 当前价 |
| Unrealized P&L | Market Value - Cost Basis |
| Realized P&L | 累计卖出收入 - 累计买入成本 |

### 期权口径

| 操作 | 记录 | P&L |
|------|------|-----|
| Sell Put | +Premium (收入) | Premium |
| Buy Put | -Premium (支出) | -Premium |
| Assignment | +Stock (接盘) | Stock P&L |
| Covered Call | -Stock (被买走) | Stock P&L |

---

## 汇率服务

支持 API：
- exchangerate-api.com
- open.er-api.com (免费)

按日折算，统一显示 RMB 价值。
