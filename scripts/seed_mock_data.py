#!/usr/bin/env python3
"""
插入模拟数据 — 用于体验前端展示效果

运行方式：
  python scripts/seed_mock_data.py          # 插入模拟数据
  python scripts/seed_mock_data.py --reset   # 清空后重新插入

包含数据：
  - 6 个账户（不同币种/类型）
  - 资金流水（DEPOSIT / WITHDRAW）
  - 投资交易（SLV 车轮策略 + AAPL 持仓 + VOO 指数）
  - 期权交易（Call 组合 + Put 交易）
  - 半年支出/收入记录
  - 年度汇总（2024-2026）
  - 5 个月度快照
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from db.connection import get_connection, init_database


def clear_data():
    """清空交易和快照数据（保留账户结构）"""
    conn = get_connection()
    cur = conn.cursor()
    for table in ["transactions", "snapshots", "yearly_summary"]:
        cur.execute(f"DELETE FROM {table}")
    cur.execute("UPDATE accounts SET balance = 0")
    conn.commit()
    conn.close()
    print("✅ 数据已清空")


def seed_accounts():
    """设置账户余额"""
    conn = get_connection()
    cur = conn.cursor()
    balances = [
        ("现金", 35000), ("美股", 42000), ("ETF", 18000),
        ("公积金", 85000), ("A股", 15000), ("港股", 8000),
    ]
    for name, balance in balances:
        cur.execute("UPDATE accounts SET balance = ? WHERE name = ?",
                    (balance, name))
    conn.commit()
    conn.close()
    print(f"✅ 账户余额已设置 ({len(balances)} 个)")


def seed_capital_flows():
    """插入入金/出金（影响投资组合收益率计算）"""
    # category 由 db.transactions.add 根据 action 自动推断
    flows = [
        ("2025-06-01", "DEPOSIT",  20000, "初始入金"),
        ("2025-08-01", "DEPOSIT",  15000, "追加资金"),
        ("2025-10-01", "DEPOSIT",  10000, "追加买入"),
        ("2025-12-15", "WITHDRAW", 3000,  "提取分红"),
        ("2026-01-15", "DEPOSIT",  8000,  "追加资金"),
    ]
    for dt, action, amount, note in flows:
        db.transactions.add(dt, action, quantity=1, price=amount,
                            currency="USD", note=note)
    print(f"✅ 资金流水已插入 ({len(flows)} 笔)")


def seed_investment_transactions():
    """插入投资交易（股票 + 期权）"""
    # category 由 db.transactions.add 根据 action 自动推断，无需手动传入
    trades = [
        # ── SLV（核心标的）──
        ("2026-01-15", "BUY",      "SLV", 100, 110.0, 1.0,  "建仓100股"),
        ("2026-02-07", "STO_CALL", "SLV", 1,   2.60,  0.65, "sell 88C 0213到期"),
        ("2026-02-07", "BTO_CALL", "SLV", 1,   4.00,  0.65, "buy 84C 0213到期"),
        ("2026-02-07", "STO_CALL", "SLV", 1,   2.35,  0.65, "sell 88C 0213到期"),

        # ── AAPL ──
        ("2025-09-10", "BUY",      "AAPL", 50,  175.0, 1.0,  "建仓"),
        ("2025-10-15", "BUY",      "AAPL", 50,  180.0, 1.0,  "加仓"),
        ("2025-11-05", "STO_CALL", "AAPL", 1,   3.50,  0.65, "sell 190C 1205到期"),
        ("2025-12-05", "STO_CALL", "AAPL", 1,   2.80,  0.65, "sell 195C 0116到期"),
        ("2026-01-16", "STO_CALL", "AAPL", 1,   4.20,  0.65, "sell 200C 0220到期"),

        # ── VOO（指数基金）──
        ("2025-06-01", "BUY", "VOO", 10, 480.0, 0, "定投"),
        ("2025-07-01", "BUY", "VOO", 10, 485.0, 0, "定投"),
        ("2025-08-01", "BUY", "VOO", 10, 490.0, 0, "定投"),
        ("2025-09-01", "BUY", "VOO", 10, 475.0, 0, "定投"),
        ("2025-10-01", "BUY", "VOO", 10, 495.0, 0, "定投"),

        # ── GLD（贵金属）──
        ("2025-08-20", "BUY", "GLD", 30, 220.0, 1.0, "建仓"),
        ("2025-11-10", "STO", "GLD", 1,  2.50,  0.65, "sell put 215P 1219到期"),

        # ── PLTR（小盘/成长）──
        ("2025-10-01", "BUY",      "PLTR", 200, 42.0,  1.0,  "建仓"),
        ("2025-12-01", "STO_CALL", "PLTR", 2,   1.80,  1.30, "sell 50C 0116到期"),
        ("2026-01-16", "BTC",      "PLTR", 2,   0.30,  1.30, "平仓 50C"),

        # ── 分红 ──
        ("2025-09-25", "DIVIDEND", "VOO",  1, 500.0,  0, "VOO 分红"),
        ("2025-12-28", "DIVIDEND", "AAPL", 1, 300.0,  0, "AAPL 分红"),
        ("2025-12-28", "DIVIDEND", "VOO",  1, 500.0,  0, "VOO 分红"),
    ]

    for t in trades:
        db.transactions.add(
            t[0], t[1], symbol=t[2], quantity=t[3],
            price=t[4], fees=t[5], currency="USD", note=t[6])
    print(f"✅ 投资交易已插入 ({len(trades)} 笔)")


def seed_expense_income():
    """插入半年的支出/收入数据"""
    # category 自动推断：INCOME→INCOME, EXPENSE→EXPENSE
    records = [
        # ── 2025-09 ──
        ("2025-09-01", "INCOME",  28000, "CNY", "工资",     "9月工资"),
        ("2025-09-03", "EXPENSE",  3500, "CNY", "房租",     "9月房租"),
        ("2025-09-05", "EXPENSE",   800, "CNY", "餐饮",     None),
        ("2025-09-08", "EXPENSE",   350, "CNY", "交通",     None),
        ("2025-09-12", "EXPENSE",  1200, "CNY", "在家吃饭", "超市采购"),
        ("2025-09-15", "EXPENSE",   450, "CNY", "外食",     None),
        ("2025-09-20", "EXPENSE",   200, "CNY", "订阅",     "Netflix+Spotify"),

        # ── 2025-10 ──
        ("2025-10-01", "INCOME",  28000, "CNY", "工资",     "10月工资"),
        ("2025-10-03", "EXPENSE",  3500, "CNY", "房租",     None),
        ("2025-10-07", "EXPENSE",   920, "CNY", "餐饮",     None),
        ("2025-10-10", "EXPENSE",   380, "CNY", "交通",     None),
        ("2025-10-14", "EXPENSE",  1100, "CNY", "在家吃饭", None),
        ("2025-10-18", "EXPENSE",   600, "CNY", "外食",     "朋友聚餐"),
        ("2025-10-22", "EXPENSE",  3000, "CNY", "家庭",     "给父母"),
        ("2025-10-28", "EXPENSE",   200, "CNY", "订阅",     None),

        # ── 2025-11 ──
        ("2025-11-01", "INCOME",  28000, "CNY", "工资",     "11月工资"),
        ("2025-11-03", "EXPENSE",  3500, "CNY", "房租",     None),
        ("2025-11-06", "EXPENSE",   750, "CNY", "餐饮",     None),
        ("2025-11-09", "EXPENSE",   300, "CNY", "交通",     None),
        ("2025-11-13", "EXPENSE",  1300, "CNY", "在家吃饭", None),
        ("2025-11-17", "EXPENSE",   520, "CNY", "外食",     None),
        ("2025-11-20", "EXPENSE",   200, "CNY", "订阅",     None),
        ("2025-11-25", "EXPENSE",   800, "CNY", "日用",     "冬装"),

        # ── 2025-12 ──
        ("2025-12-01", "INCOME",  28000, "CNY", "工资",     "12月工资"),
        ("2025-12-01", "INCOME",  50000, "CNY", "工资",     "年终奖"),
        ("2025-12-03", "EXPENSE",  3500, "CNY", "房租",     None),
        ("2025-12-06", "EXPENSE",   880, "CNY", "餐饮",     None),
        ("2025-12-10", "EXPENSE",   400, "CNY", "交通",     None),
        ("2025-12-15", "EXPENSE",  1500, "CNY", "在家吃饭", "圣诞大采购"),
        ("2025-12-20", "EXPENSE",  1200, "CNY", "外食",     "年底聚餐"),
        ("2025-12-22", "EXPENSE",  5000, "CNY", "家庭",     "给父母+压岁钱"),
        ("2025-12-25", "EXPENSE",   200, "CNY", "订阅",     None),

        # ── 2026-01 ──
        ("2026-01-01", "INCOME",  30000, "CNY", "工资",     "1月工资（调薪）"),
        ("2026-01-03", "EXPENSE",  3800, "CNY", "房租",     "新年涨租"),
        ("2026-01-06", "EXPENSE",   950, "CNY", "餐饮",     None),
        ("2026-01-10", "EXPENSE",   350, "CNY", "交通",     None),
        ("2026-01-15", "EXPENSE",  1100, "CNY", "在家吃饭", None),
        ("2026-01-20", "EXPENSE",   480, "CNY", "外食",     None),
        ("2026-01-25", "EXPENSE",   200, "CNY", "订阅",     None),

        # ── 2026-02 ──
        ("2026-02-01", "INCOME",  30000, "CNY", "工资",     "2月工资"),
        ("2026-02-03", "EXPENSE",  3800, "CNY", "房租",     None),
        ("2026-02-05", "EXPENSE",  1500, "CNY", "餐饮",     "春节聚餐"),
        ("2026-02-05", "EXPENSE",  6000, "CNY", "家庭",     "过年红包"),
        ("2026-02-07", "EXPENSE",   300, "CNY", "交通",     None),
        ("2026-02-07", "EXPENSE",   200, "CNY", "订阅",     None),
    ]

    for r in records:
        db.transactions.add(
            r[0], r[1], quantity=1, price=r[2],
            currency=r[3], subcategory=r[4], note=r[5])
    print(f"✅ 支出/收入记录已插入 ({len(records)} 笔)")


def seed_yearly_summary():
    """插入年度汇总"""
    years = [
        (2024, 320000, 48000, 28000, 12000, "全年"),
        (2025, 336000, 50000, 32000, 18500, "含年终奖"),
        (2026, 360000, 54000, 35000, 8000,  "预估"),
    ]
    for y in years:
        db.yearly.upsert(
            y[0], pre_tax_income=y[1], social_insurance=y[2],
            income_tax=y[3], investment_income=y[4], note=y[5])
    print(f"✅ 年度汇总已插入 ({len(years)} 年)")


def seed_snapshots():
    """插入月度快照"""
    snaps = [
        ("2025-10-01", 55000, 396000, "10月快照"),
        ("2025-11-01", 58000, 417600, "11月快照"),
        ("2025-12-01", 60000, 432000, "12月快照"),
        ("2026-01-01", 63000, 453600, "1月快照"),
        ("2026-02-01", 65000, 468000, "2月快照"),
    ]
    for s in snaps:
        db.snapshots.create(
            date_str=s[0], total_assets_usd=s[1],
            total_assets_rmb=s[2], assets_data={"accounts": []},
            note=s[3])
    print(f"✅ 月度快照已插入 ({len(snaps)} 个)")


def main():
    reset = "--reset" in sys.argv

    print("=" * 50)
    print("🌱 插入模拟数据")
    print("=" * 50)

    init_database()

    if reset:
        clear_data()

    seed_accounts()
    seed_capital_flows()
    seed_investment_transactions()
    seed_expense_income()
    seed_yearly_summary()
    seed_snapshots()

    print("=" * 50)
    print("✅ 全部完成！运行 `streamlit run app.py` 查看效果")
    print("=" * 50)


if __name__ == "__main__":
    main()
