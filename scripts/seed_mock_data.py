#!/usr/bin/env python3
"""
插入模拟数据 - 用于体验前端展示效果

运行方式：
  python scripts/seed_mock_data.py          # 插入模拟数据
  python scripts/seed_mock_data.py --reset   # 清空后重新插入

包含数据：
  - 3 个账户（美元、人民币、港币）
  - 投资交易（SLV 车轮策略 + AAPL 持仓 + VOO 指数）
  - 期权交易（题目中的 Call 组合 + 额外 Put 交易）
  - 半年支出/收入记录
  - 年度汇总（2024-2026）
  - 3 个月度快照
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database_v2 import (
    init_database, get_connection,
    add_transaction, update_yearly_summary, create_snapshot,
)


def clear_data():
    """清空交易和快照数据（保留账户结构）"""
    conn = get_connection()
    cur = conn.cursor()
    for table in ["transactions", "snapshots", "yearly_summary", "strategies"]:
        cur.execute(f"DELETE FROM {table}")
    # 重置账户余额
    cur.execute("UPDATE accounts SET balance = 0")
    conn.commit()
    conn.close()
    print("✅ 数据已清空")


def seed_accounts():
    """设置账户余额"""
    conn = get_connection()
    cur = conn.cursor()
    balances = [
        ("现金",   35000),
        ("美股",   42000),
        ("ETF",    18000),
        ("公积金", 85000),
        ("A股",    15000),
        ("港股",   8000),
    ]
    for name, balance in balances:
        cur.execute("UPDATE accounts SET balance = ? WHERE name = ?", (balance, name))
    conn.commit()
    conn.close()
    print(f"✅ 账户余额已设置 ({len(balances)} 个)")


def seed_investment_transactions():
    """插入投资交易（股票 + 期权）"""
    trades = [
        # ── SLV（题目中的核心标的）──
        # 买入 100 股 @ $110
        ("2026-01-15", "BUY",      "SLV", 100, 110.0, 1.0,  "USD", "投资", None, None, "建仓100股"),
        # 卖出 1 张 88C @2.60
        ("2026-02-07", "STO_CALL", "SLV", 1,   2.60,  0.65, "USD", "投资", None, None, "sell 88C 0213到期"),
        # 买入 1 张 84C @4.00
        ("2026-02-07", "BTO_CALL", "SLV", 1,   4.00,  0.65, "USD", "投资", None, None, "buy 84C 0213到期"),
        # 卖出 1 张 88C @2.35
        ("2026-02-07", "STO_CALL", "SLV", 1,   2.35,  0.65, "USD", "投资", None, None, "sell 88C 0213到期"),

        # ── AAPL ──
        ("2025-09-10", "BUY",      "AAPL", 50,  175.0, 1.0,  "USD", "投资", None, None, "建仓"),
        ("2025-10-15", "BUY",      "AAPL", 50,  180.0, 1.0,  "USD", "投资", None, None, "加仓"),
        ("2025-11-05", "STO_CALL", "AAPL", 1,   3.50,  0.65, "USD", "投资", None, None, "sell 190C 1205到期"),
        ("2025-12-05", "STO_CALL", "AAPL", 1,   2.80,  0.65, "USD", "投资", None, None, "sell 195C 0116到期"),
        ("2026-01-16", "STO_CALL", "AAPL", 1,   4.20,  0.65, "USD", "投资", None, None, "sell 200C 0220到期"),

        # ── VOO（指数基金）──
        ("2025-06-01", "BUY",      "VOO",  10,  480.0, 0,    "USD", "投资", None, None, "定投"),
        ("2025-07-01", "BUY",      "VOO",  10,  485.0, 0,    "USD", "投资", None, None, "定投"),
        ("2025-08-01", "BUY",      "VOO",  10,  490.0, 0,    "USD", "投资", None, None, "定投"),
        ("2025-09-01", "BUY",      "VOO",  10,  475.0, 0,    "USD", "投资", None, None, "定投"),
        ("2025-10-01", "BUY",      "VOO",  10,  495.0, 0,    "USD", "投资", None, None, "定投"),

        # ── GLD（贵金属）──
        ("2025-08-20", "BUY",      "GLD",  30,  220.0, 1.0,  "USD", "投资", None, None, "建仓"),
        ("2025-11-10", "STO",      "GLD",  1,   2.50,  0.65, "USD", "投资", None, None, "sell put 215P 1219到期"),

        # ── PLTR（小盘/成长）──
        ("2025-10-01", "BUY",      "PLTR", 200, 42.0,  1.0,  "USD", "投资", None, None, "建仓"),
        ("2025-12-01", "STO_CALL", "PLTR", 2,   1.80,  1.30, "USD", "投资", None, None, "sell 50C 0116到期"),
        ("2026-01-16", "BTC",      "PLTR", 2,   0.30,  1.30, "USD", "投资", None, None, "平仓 50C"),
    ]

    for t in trades:
        add_transaction(
            datetime_str=t[0],
            action=t[1],
            symbol=t[2],
            quantity=t[3],
            price=t[4],
            fees=t[5],
            currency=t[6],
            category=t[7],
            subcategory=t[8],
            target=t[9],
            note=t[10],
        )
    print(f"✅ 投资交易已插入 ({len(trades)} 笔)")


def seed_expense_income():
    """插入半年的支出/收入数据"""
    records = [
        # ── 2025-09 ──
        ("2025-09-01", "INCOME",  1, 28000, "CNY", "收入", "工资",     None, "9月工资"),
        ("2025-09-03", "EXPENSE", 1, 3500,  "CNY", "支出", "房租",     None, "9月房租"),
        ("2025-09-05", "EXPENSE", 1, 800,   "CNY", "支出", "餐饮",     None, None),
        ("2025-09-08", "EXPENSE", 1, 350,   "CNY", "支出", "交通",     None, None),
        ("2025-09-12", "EXPENSE", 1, 1200,  "CNY", "支出", "在家吃饭", None, "超市采购"),
        ("2025-09-15", "EXPENSE", 1, 450,   "CNY", "支出", "外食",     None, None),
        ("2025-09-20", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, "Netflix+Spotify"),
        ("2025-09-25", "INCOME",  1, 500,   "USD", "收入", "分红",     None, "VOO分红"),

        # ── 2025-10 ──
        ("2025-10-01", "INCOME",  1, 28000, "CNY", "收入", "工资",     None, "10月工资"),
        ("2025-10-03", "EXPENSE", 1, 3500,  "CNY", "支出", "房租",     None, None),
        ("2025-10-07", "EXPENSE", 1, 920,   "CNY", "支出", "餐饮",     None, None),
        ("2025-10-10", "EXPENSE", 1, 380,   "CNY", "支出", "交通",     None, None),
        ("2025-10-14", "EXPENSE", 1, 1100,  "CNY", "支出", "在家吃饭", None, None),
        ("2025-10-18", "EXPENSE", 1, 600,   "CNY", "支出", "外食",     None, "朋友聚餐"),
        ("2025-10-22", "EXPENSE", 1, 3000,  "CNY", "支出", "家庭",     None, "给父母"),
        ("2025-10-28", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, None),

        # ── 2025-11 ──
        ("2025-11-01", "INCOME",  1, 28000, "CNY", "收入", "工资",     None, "11月工资"),
        ("2025-11-03", "EXPENSE", 1, 3500,  "CNY", "支出", "房租",     None, None),
        ("2025-11-06", "EXPENSE", 1, 750,   "CNY", "支出", "餐饮",     None, None),
        ("2025-11-09", "EXPENSE", 1, 300,   "CNY", "支出", "交通",     None, None),
        ("2025-11-13", "EXPENSE", 1, 1300,  "CNY", "支出", "在家吃饭", None, None),
        ("2025-11-17", "EXPENSE", 1, 520,   "CNY", "支出", "外食",     None, None),
        ("2025-11-20", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, None),
        ("2025-11-25", "EXPENSE", 1, 800,   "CNY", "支出", "日用",     None, "冬装"),

        # ── 2025-12 ──
        ("2025-12-01", "INCOME",  1, 28000, "CNY", "收入", "工资",     None, "12月工资"),
        ("2025-12-01", "INCOME",  1, 50000, "CNY", "收入", "工资",     None, "年终奖"),
        ("2025-12-03", "EXPENSE", 1, 3500,  "CNY", "支出", "房租",     None, None),
        ("2025-12-06", "EXPENSE", 1, 880,   "CNY", "支出", "餐饮",     None, None),
        ("2025-12-10", "EXPENSE", 1, 400,   "CNY", "支出", "交通",     None, None),
        ("2025-12-15", "EXPENSE", 1, 1500,  "CNY", "支出", "在家吃饭", None, "圣诞大采购"),
        ("2025-12-20", "EXPENSE", 1, 1200,  "CNY", "支出", "外食",     None, "年底聚餐"),
        ("2025-12-22", "EXPENSE", 1, 5000,  "CNY", "支出", "家庭",     None, "给父母+压岁钱"),
        ("2025-12-25", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, None),
        ("2025-12-28", "INCOME",  1, 800,   "USD", "收入", "分红",     None, "AAPL+VOO分红"),

        # ── 2026-01 ──
        ("2026-01-01", "INCOME",  1, 30000, "CNY", "收入", "工资",     None, "1月工资（调薪）"),
        ("2026-01-03", "EXPENSE", 1, 3800,  "CNY", "支出", "房租",     None, "新年涨租"),
        ("2026-01-06", "EXPENSE", 1, 950,   "CNY", "支出", "餐饮",     None, None),
        ("2026-01-10", "EXPENSE", 1, 350,   "CNY", "支出", "交通",     None, None),
        ("2026-01-15", "EXPENSE", 1, 1100,  "CNY", "支出", "在家吃饭", None, None),
        ("2026-01-20", "EXPENSE", 1, 480,   "CNY", "支出", "外食",     None, None),
        ("2026-01-25", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, None),

        # ── 2026-02 ──
        ("2026-02-01", "INCOME",  1, 30000, "CNY", "收入", "工资",     None, "2月工资"),
        ("2026-02-03", "EXPENSE", 1, 3800,  "CNY", "支出", "房租",     None, None),
        ("2026-02-05", "EXPENSE", 1, 1500,  "CNY", "支出", "餐饮",     None, "春节聚餐"),
        ("2026-02-05", "EXPENSE", 1, 6000,  "CNY", "支出", "家庭",     None, "过年红包"),
        ("2026-02-07", "EXPENSE", 1, 300,   "CNY", "支出", "交通",     None, None),
        ("2026-02-07", "EXPENSE", 1, 200,   "CNY", "支出", "订阅",     None, None),
    ]

    for r in records:
        add_transaction(
            datetime_str=r[0],
            action=r[1],
            quantity=r[2],
            price=r[3],
            currency=r[4],
            category=r[5],
            subcategory=r[6],
            target=r[7],
            note=r[8],
        )
    print(f"✅ 支出/收入记录已插入 ({len(records)} 笔)")


def seed_yearly_summary():
    """插入年度汇总"""
    years = [
        (2024, 320000, 48000, 28000, 12000, "全年"),
        (2025, 336000, 50000, 32000, 18500, "含年终奖"),
        (2026, 360000, 54000, 35000, 8000,  "预估"),
    ]
    for y in years:
        update_yearly_summary(*y)
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
        create_snapshot(
            date_str=s[0],
            total_assets_usd=s[1],
            total_assets_rmb=s[2],
            assets_data={"accounts": []},
            note=s[3],
        )
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
    seed_investment_transactions()
    seed_expense_income()
    seed_yearly_summary()
    seed_snapshots()

    print("=" * 50)
    print("✅ 全部完成！运行 `streamlit run app_v2.py` 查看效果")
    print("=" * 50)


if __name__ == "__main__":
    main()
