#!/usr/bin/env python3
"""
单元测试：期权策略盈亏计算

核心测试场景
============
持有 100 股，成本价 $110，现价 $80
期权操作（全部下周五到期 2026-02-13）：
  1) 卖出 1 张 88C，权利金 $2.60（收入 $260）
  2) 买入 1 张 84C，权利金 $4.00（支出 $400）
  3) 卖出 1 张 88C，权利金 $2.35（收入 $235）

净权利金 = $260 - $400 + $235 = +$95（净收入）

到期时各价位 P&L 分析
─────────────────────────────────────────────
价格区间        | 公式
─────────────────────────────────────────────
Price ≤ $84     | (Price-110)×100 + $95
$84 < P ≤ $88  | (Price-110)×100 + $95 + (Price-84)×100
Price > $88     | 固定 -$1,705
─────────────────────────────────────────────

具体数值：
  Price=$70  → -$4,000 + $95 = -$3,905
  Price=$80  → -$3,000 + $95 = -$2,905
  Price=$84  → -$2,600 + $95 = -$2,505
  Price=$86  → -$2,400 + $95 + $200 = -$2,105
  Price=$88  → -$2,200 + $95 + $400 = -$1,705
  Price=$90  → -$2,000 + $95 + $600 - $400 = -$1,705
  Price=$100 → -$1,000 + $95 + $1,600 - $2,400 = -$1,705
  Price=$110 → $0 + $95 + $2,600 - $4,400 = -$1,705
  Price=$120 → $1,000 + $95 + $3,600 - $6,400 = -$1,705
"""

import sys
import unittest
from pathlib import Path

# 让测试能找到 src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Transaction, TransactionType


# ═══════════════════════════════════════════════════════
#  辅助函数：纯数学 P&L 计算（作为 ground truth）
# ═══════════════════════════════════════════════════════

def stock_pnl(shares: int, cost: float, price_at_expiry: float) -> float:
    """股票浮动盈亏"""
    return (price_at_expiry - cost) * shares


def call_option_payoff_at_expiry(
    strike: float,
    premium: float,
    contracts: int,
    is_long: bool,
) -> float:
    """
    单一 Call 期权到期时 P&L（含权利金成本/收入）

    Args:
        strike: 行权价
        premium: 每股权利金
        contracts: 合约数量（1 合约 = 100 股）
        is_long: True=买入方, False=卖出方

    Returns:
        P&L（美元），对于卖方正值=赚钱
    """
    # 注意：这里返回的是"在任意到期价格下"的参数化函数
    # 所以我们把它做成返回 lambda
    raise NotImplementedError("请使用 call_pnl_at_price")


def call_pnl_at_price(
    price: float,
    strike: float,
    premium: float,
    contracts: int,
    is_long: bool,
) -> float:
    """
    Call 期权到期时在指定价格下的 P&L

    Long Call P&L  = max(price - strike, 0) × 100 × contracts - premium × 100 × contracts
    Short Call P&L = premium × 100 × contracts - max(price - strike, 0) × 100 × contracts
    """
    intrinsic = max(price - strike, 0)
    multiplier = 100 * contracts

    if is_long:
        return (intrinsic - premium) * multiplier
    else:
        return (premium - intrinsic) * multiplier


def total_position_pnl(
    price_at_expiry: float,
    shares: int = 100,
    stock_cost: float = 110.0,
) -> float:
    """
    计算完整持仓（股票 + 3 笔期权）在到期时的总 P&L

    持仓：
      - Long 100 shares @ $110
      - Short 1x 88C @ $2.60
      - Long  1x 84C @ $4.00
      - Short 1x 88C @ $2.35
    """
    pnl = stock_pnl(shares, stock_cost, price_at_expiry)

    # 卖出 1 张 88C，收 $2.60
    pnl += call_pnl_at_price(price_at_expiry, strike=88, premium=2.60, contracts=1, is_long=False)
    # 买入 1 张 84C，付 $4.00
    pnl += call_pnl_at_price(price_at_expiry, strike=84, premium=4.00, contracts=1, is_long=True)
    # 卖出 1 张 88C，收 $2.35
    pnl += call_pnl_at_price(price_at_expiry, strike=88, premium=2.35, contracts=1, is_long=False)

    return pnl


# ═══════════════════════════════════════════════════════
#  构造 Transaction 对象的辅助函数
# ═══════════════════════════════════════════════════════

def make_stock_buy(symbol, shares, cost_per_share, date="2026-01-15"):
    """构造一笔股票买入交易"""
    return Transaction(
        type=TransactionType.STOCK,
        subtype="buy",
        date=date,
        amount=shares * cost_per_share,   # 正数 = 支出
        symbol=symbol,
        quantity=shares,
        price=cost_per_share,
    )


def make_sell_call(symbol, contracts, premium, strike, expiry, date="2026-02-07"):
    """构造一笔卖出 Call 交易"""
    return Transaction(
        type=TransactionType.OPTION,
        subtype="sell_call",
        date=date,
        amount=-(contracts * 100 * premium),  # 负数 = 收入
        symbol=symbol,
        quantity=contracts,
        price=premium,
        strike_price=strike,
        expiration_date=expiry,
        option_direction=-1,
    )


def make_buy_call(symbol, contracts, premium, strike, expiry, date="2026-02-07"):
    """构造一笔买入 Call 交易"""
    return Transaction(
        type=TransactionType.OPTION,
        subtype="buy_call",
        date=date,
        amount=contracts * 100 * premium,  # 正数 = 支出
        symbol=symbol,
        quantity=contracts,
        price=premium,
        strike_price=strike,
        expiration_date=expiry,
        option_direction=1,
    )


def build_scenario_transactions(symbol="SLV"):
    """构建题目中的完整交易序列"""
    return [
        # 1. 买入 100 股 @ $110
        make_stock_buy(symbol, 100, 110.0, date="2026-01-15"),
        # 2. 卖出 1 张 88C，权利金 $2.60
        make_sell_call(symbol, 1, 2.60, strike=88, expiry="2026-02-13", date="2026-02-07"),
        # 3. 买入 1 张 84C，权利金 $4.00
        make_buy_call(symbol, 1, 4.00, strike=84, expiry="2026-02-13", date="2026-02-07"),
        # 4. 卖出 1 张 88C，权利金 $2.35
        make_sell_call(symbol, 1, 2.35, strike=88, expiry="2026-02-13", date="2026-02-07"),
    ]


# ═══════════════════════════════════════════════════════
#  测试类
# ═══════════════════════════════════════════════════════

class TestCallPnlAtPrice(unittest.TestCase):
    """测试单一 Call 期权的到期 P&L 计算"""

    def test_long_call_itm(self):
        """买入 84C @ $4.00，到期价 $90"""
        pnl = call_pnl_at_price(90, strike=84, premium=4.0, contracts=1, is_long=True)
        # (90-84-4) × 100 = $200
        self.assertAlmostEqual(pnl, 200.0)

    def test_long_call_otm(self):
        """买入 84C @ $4.00，到期价 $80 → 归零"""
        pnl = call_pnl_at_price(80, strike=84, premium=4.0, contracts=1, is_long=True)
        # max(80-84,0) - 4.0 = -4.0, ×100 = -$400
        self.assertAlmostEqual(pnl, -400.0)

    def test_long_call_at_strike(self):
        """买入 84C @ $4.00，到期价 $84 → 只剩权利金损失"""
        pnl = call_pnl_at_price(84, strike=84, premium=4.0, contracts=1, is_long=True)
        self.assertAlmostEqual(pnl, -400.0)

    def test_short_call_otm(self):
        """卖出 88C @ $2.60，到期价 $85 → 赚全部权利金"""
        pnl = call_pnl_at_price(85, strike=88, premium=2.6, contracts=1, is_long=False)
        self.assertAlmostEqual(pnl, 260.0)

    def test_short_call_itm(self):
        """卖出 88C @ $2.60，到期价 $95 → 亏损"""
        pnl = call_pnl_at_price(95, strike=88, premium=2.6, contracts=1, is_long=False)
        # (2.6 - (95-88)) × 100 = (2.6 - 7) × 100 = -$440
        self.assertAlmostEqual(pnl, -440.0)

    def test_short_call_at_strike(self):
        """卖出 88C @ $2.60，到期价 $88 → 赚全部权利金"""
        pnl = call_pnl_at_price(88, strike=88, premium=2.6, contracts=1, is_long=False)
        self.assertAlmostEqual(pnl, 260.0)


class TestTotalPositionPnl(unittest.TestCase):
    """
    测试完整持仓在各到期价下的总 P&L

    持仓：100 股 @ $110 + 期权组合
    净权利金 = $260 - $400 + $235 = $95
    """

    def test_net_premium(self):
        """验证净权利金 = $95"""
        # 三笔期权在 OTM 时的纯权利金
        p1 = call_pnl_at_price(70, 88, 2.60, 1, False)   # +260
        p2 = call_pnl_at_price(70, 84, 4.00, 1, True)    # -400
        p3 = call_pnl_at_price(70, 88, 2.35, 1, False)   # +235
        self.assertAlmostEqual(p1 + p2 + p3, 95.0)

    def test_price_70(self):
        """Price=$70: 深度亏损"""
        pnl = total_position_pnl(70)
        # Stock: (70-110)*100 = -4000, Options: +95
        self.assertAlmostEqual(pnl, -3905.0)

    def test_price_80_current(self):
        """Price=$80: 当前价格"""
        pnl = total_position_pnl(80)
        # Stock: -3000, Options: +95
        self.assertAlmostEqual(pnl, -2905.0)

    def test_price_84_at_lower_strike(self):
        """Price=$84: 刚好触及买入 Call 行权价"""
        pnl = total_position_pnl(84)
        # Stock: -2600, Long 84C intrinsic=0, all options net=$95
        self.assertAlmostEqual(pnl, -2505.0)

    def test_price_86_between_strikes(self):
        """Price=$86: 在两个行权价之间"""
        pnl = total_position_pnl(86)
        # Stock: -2400
        # Long 84C: (86-84-4)*100 = -200
        # Short 88C x2: +260+235 = +495
        # Total options: -200 + 495 = 295
        # Total: -2400 + 295 = -2105 ✓
        #
        # 或简化: (86-110)*100 + 95 + (86-84)*100 = -2400 + 95 + 200 = -2105
        self.assertAlmostEqual(pnl, -2105.0)

    def test_price_88_at_upper_strike(self):
        """Price=$88: 到达卖出 Call 行权价 → 最佳情况的起始点"""
        pnl = total_position_pnl(88)
        # Stock: -2200, Long 84C: (88-84-4)*100=0, Short 88C: +495
        # = -2200 + 0 + 495 = -1705
        self.assertAlmostEqual(pnl, -1705.0)

    def test_price_90_above_strikes(self):
        """Price=$90: 盈亏不再变化"""
        pnl = total_position_pnl(90)
        self.assertAlmostEqual(pnl, -1705.0)

    def test_price_100(self):
        """Price=$100: 大幅反弹，P&L 仍锁定"""
        pnl = total_position_pnl(100)
        self.assertAlmostEqual(pnl, -1705.0)

    def test_price_110_breakeven_stock(self):
        """Price=$110: 股票回本价，但期权组合仍有影响"""
        pnl = total_position_pnl(110)
        self.assertAlmostEqual(pnl, -1705.0)

    def test_price_120_well_above(self):
        """Price=$120: 远高于行权价"""
        pnl = total_position_pnl(120)
        self.assertAlmostEqual(pnl, -1705.0)

    def test_price_50_crash(self):
        """Price=$50: 股价暴跌"""
        pnl = total_position_pnl(50)
        # Stock: -6000, Options: +95
        self.assertAlmostEqual(pnl, -5905.0)

    def test_pnl_monotonic_below_84(self):
        """价格 < $84 区间：P&L 随价格线性下降"""
        for p in [60, 65, 70, 75, 80]:
            expected = (p - 110) * 100 + 95
            self.assertAlmostEqual(total_position_pnl(p), expected)

    def test_pnl_between_strikes(self):
        """$84 < 价格 ≤ $88 区间：P&L 每 $1 改善 $200"""
        for p in [85, 86, 87, 88]:
            expected = (p - 110) * 100 + 95 + (p - 84) * 100
            self.assertAlmostEqual(total_position_pnl(p), expected)

    def test_pnl_flat_above_88(self):
        """价格 > $88 区间：P&L 固定在 -$1,705"""
        for p in [89, 90, 95, 100, 110, 120, 150, 200]:
            self.assertAlmostEqual(total_position_pnl(p), -1705.0)

    def test_max_profit_is_minus_1705(self):
        """此策略的最大 "利润"（最小亏损）= -$1,705"""
        prices = list(range(50, 200))
        max_pnl = max(total_position_pnl(p) for p in prices)
        self.assertAlmostEqual(max_pnl, -1705.0)


class TestWithCalculatorEngine(unittest.TestCase):
    """
    使用项目中的 WheelCalculator / PortfolioCalculator 引擎
    验证其计算逻辑是否与手动计算一致
    """

    def setUp(self):
        from src import WheelCalculator, PortfolioCalculator
        self.symbol = "SLV"
        self.txs = build_scenario_transactions(self.symbol)
        self.wheel = WheelCalculator(self.txs)
        self.portfolio = PortfolioCalculator(self.txs)

    def test_current_shares(self):
        """验证当前持仓 = 100 股"""
        basis = self.wheel.calculate_adjusted_cost_basis(self.symbol)
        self.assertEqual(basis["current_shares"], 100)

    def test_total_premiums(self):
        """
        验证期权权利金统计
        收入: $260 + $235 = $495
        支出: $400
        净: $95
        """
        premiums = self.wheel.option_calc.get_premiums_summary(self.symbol)
        self.assertAlmostEqual(premiums["total_collected"], 495.0)
        self.assertAlmostEqual(premiums["total_paid"], 400.0)
        self.assertAlmostEqual(premiums["net_premium"], 95.0)

    def test_option_positions(self):
        """验证期权仓位: short 2 call, long 1 call → net call = -1"""
        pos = self.wheel.option_calc.calculate_option_positions(self.symbol)
        # Short 2 calls + Long 1 call = net -1 call
        self.assertEqual(pos["call"], -1)
        self.assertEqual(pos["put"], 0)

    def test_adjusted_cost_basis(self):
        """
        调整后成本 = (股票成本 + 期权净支出(含符号) + 手续费) / 持仓

        premiums_from_options = -260 + 400 + (-235) = -95 (净收入)
        net_cost = 11000 + (-95) + 0 = 10905
        adjusted_cost = 10905 / 100 = $109.05
        """
        basis = self.wheel.calculate_adjusted_cost_basis(self.symbol)
        self.assertAlmostEqual(basis["total_premiums"], -95.0)
        self.assertAlmostEqual(basis["cost_basis"], 10905.0)
        self.assertAlmostEqual(basis["adjusted_cost"], 109.05)

    def test_unrealized_pnl_at_80(self):
        """现价 $80 的浮动盈亏"""
        result = self.wheel.calculate_unrealized_pnl(self.symbol, 80.0)
        # unrealized = market_value - cost_basis
        # market_value = 100 * 80 = 8000
        self.assertEqual(result["market_value"], 8000.0)
        self.assertEqual(result["current_shares"], 100)

    def test_campaign_summary(self):
        """验证车轮策略汇总"""
        summary = self.wheel.calculate_campaign_summary(self.symbol, 80.0)
        self.assertEqual(summary["symbol"], self.symbol)
        self.assertEqual(summary["current_shares"], 100)
        self.assertIsInstance(summary["total_pnl"], (int, float))

    def test_portfolio_summary_has_symbol(self):
        """组合汇总中应该包含我们的标的"""
        summary = self.portfolio.get_portfolio_summary({"SLV": 80.0})
        self.assertIn(self.symbol, summary["holdings"])


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_empty_transactions(self):
        """空交易列表不应崩溃"""
        from src import WheelCalculator
        calc = WheelCalculator([])
        basis = calc.calculate_adjusted_cost_basis("AAPL")
        self.assertEqual(basis["current_shares"], 0)

    def test_only_options_no_stock(self):
        """只有期权、没有股票时的行为"""
        from src import WheelCalculator
        txs = [
            make_sell_call("AAPL", 1, 3.0, 150, "2026-03-01"),
        ]
        calc = WheelCalculator(txs)
        basis = calc.calculate_adjusted_cost_basis("AAPL")
        self.assertEqual(basis["current_shares"], 0)

    def test_single_short_call(self):
        """卖出单个 Call 的权利金统计"""
        from src import WheelCalculator
        txs = [
            make_stock_buy("AAPL", 100, 150),
            make_sell_call("AAPL", 1, 3.0, 155, "2026-03-01"),
        ]
        calc = WheelCalculator(txs)
        premiums = calc.option_calc.get_premiums_summary("AAPL")
        self.assertAlmostEqual(premiums["total_collected"], 300.0)
        self.assertAlmostEqual(premiums["total_paid"], 0.0)
        self.assertAlmostEqual(premiums["net_premium"], 300.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
