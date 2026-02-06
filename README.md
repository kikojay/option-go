# Option Wheel Tracker

期权交易管理 + 个人资产管理工具

## 功能

- 🎯 **Wheel Strategy 管理**：跟踪期权策略周期、计算调整后成本基准
- 📊 **盈亏分析**：Realized P&L、Unrealized P&L、收益率热力图
- 💰 **资产管理**：股票持仓、账户余额、收支记录
- 📱 **多端访问**：Streamlit 网页 + Telegram Bot

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行

```bash
# 开发模式
streamlit run app.py

# 或指定端口
streamlit run app.py --server.port 8501
```

### 3. 访问

- 本地：http://localhost:8501
- 远程：通过 SSH 隧道访问

## 项目结构

```
option-go/
├── app.py              # Streamlit 主入口
├── requirements.txt    # 依赖
├── data/              # SQLite 数据库
└── src/
    ├── __init__.py
    ├── database.py    # 数据库操作
    ├── models.py       # 数据模型
    ├── calculator.py   # 盈亏计算
    ├── charts.py       # 可视化图表
    └── telegram_handler.py  # Telegram 交互
```

## Telegram 命令

```
# 期权
卖 SLV 88 put @2.5
买 SLV 88 put @1.2
接盘 SLV 100股 @80

# 股票
买入 AAPL 10股 @180
卖出 AAPL 10股 @185

# 记账
支出 餐饮 500
收入 工资 10000

# 查询
portfolio  # 资产汇总
pnl        # 盈亏情况
status     # 账户状态
```

## 数据备份

```bash
# 同步到本地 Mac
scp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/
```
