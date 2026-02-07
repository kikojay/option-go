"""
测试计算器修复的测试用例
验证 amount 符号约定的正确性

使用新的模块化导入
"""
from src.models import Transaction, TransactionType
from src.options import WheelStrategyCalculator


def test_option_pnl_simple():
    """测试简单的期权盈亏计算"""
    transactions = [
        # Sell Put @100，收入100（amount = -100）
        Transaction(
            type=TransactionType.OPTION,
            subtype="sell_put",
            date="2026-01-01",
            amount=-100,
            symbol="AAPL",
            quantity=1,
            price=1.0,
            fees=0
        ),
        # Buy Put @50，支出50（amount = 50）
        Transaction(
            type=TransactionType.OPTION,
            subtype="buy_put",
            date="2026-01-02",
            amount=50,
            symbol="AAPL",
            quantity=1,
            price=0.5,
            fees=0
        ),
    ]

    calculator = WheelStrategyCalculator(transactions)
    # 期权盈亏需要通过option_calc计算
    option_calc = calculator.option_calc
    pnl_result = option_calc.calculate_option_pnl("AAPL")

    # 期权盈亏 = -(-100) + -(50) = 100 - 50 = 50
    print(f"✓ Option PNL Test: {pnl_result['total_pnl']} (expected 50)")
    assert pnl_result["total_pnl"] == 50, f"Expected 50, got {pnl_result['total_pnl']}"


def test_adjusted_cost_basis():
    """测试调整成本基准计算"""
    transactions = [
        # 买入 100 股 @ $100，支出 10000（amount = 10000）
        Transaction(
            type=TransactionType.STOCK,
            subtype="buy",
            date="2026-01-01",
            amount=10000,
            symbol="AAPL",
            quantity=100,
            price=100,
            fees=10
        ),
        # 卖出 Sell Put 权利金，收入 200（amount = -200）
        Transaction(
            type=TransactionType.OPTION,
            subtype="sell_put",
            date="2026-01-02",
            amount=-200,
            symbol="AAPL",
            quantity=1,
            price=2.0,
            fees=0
        ),
    ]

    calculator = WheelStrategyCalculator(transactions)
    basis = calculator.calculate_adjusted_cost_basis("AAPL")

    # 调整成本 = (10000 - (-200) + 10) / 100 = 10210 / 100 = 102.1
    expected_cost = (10000 - (-200) + 10) / 100
    print(f"✓ Cost Basis Test: {basis['adjusted_cost']} (expected {expected_cost})")
    assert abs(basis["adjusted_cost"] - expected_cost) < 0.01, \
        f"Expected {expected_cost}, got {basis['adjusted_cost']}"
    assert basis["current_shares"] == 100


def test_realized_pnl():
    """测试已实现盈亏计算"""
    transactions = [
        # 买入 100 股 @ $100，支出 10000
        Transaction(
            type=TransactionType.STOCK,
            subtype="buy",
            date="2026-01-01",
            amount=10000,
            symbol="AAPL",
            quantity=100,
            price=100,
            fees=10
        ),
        # 卖出 100 股 @ $110，收入 11000（amount = -11000）
        Transaction(
            type=TransactionType.STOCK,
            subtype="sell",
            date="2026-02-01",
            amount=-11000,
            symbol="AAPL",
            quantity=100,
            price=110,
            fees=10
        ),
        # 卖出 Sell Call 权利金，收入 100（amount = -100）
        Transaction(
            type=TransactionType.OPTION,
            subtype="sell_call",
            date="2026-01-02",
            amount=-100,
            symbol="AAPL",
            quantity=1,
            price=1.0,
            fees=0
        ),
    ]

    calculator = WheelStrategyCalculator(transactions)
    realized = calculator.calculate_realized_pnl("AAPL")

    # 已实现盈亏 = (卖出收入 - 购入成本) + 期权收益 - 手续费
    # = (11000 - 10000) + 100 - (10 + 10)
    # = 1000 + 100 - 20
    # = 1080
    expected_realized = (11000 - 10000) + 100 - 20
    print(f"✓ Realized PNL Test: {realized} (expected {expected_realized})")
    assert realized == expected_realized, f"Expected {expected_realized}, got {realized}"


def test_unrealized_pnl():
    """测试未实现盈亏计算"""
    transactions = [
        # 买入 100 股 @ $100，支出 10000
        Transaction(
            type=TransactionType.STOCK,
            subtype="buy",
            date="2026-01-01",
            amount=10000,
            symbol="AAPL",
            quantity=100,
            price=100,
            fees=10
        ),
        # 卖出 Sell Put 权利金，收入 200（amount = -200）
        Transaction(
            type=TransactionType.OPTION,
            subtype="sell_put",
            date="2026-01-02",
            amount=-200,
            symbol="AAPL",
            quantity=1,
            price=2.0,
            fees=0
        ),
    ]

    calculator = WheelStrategyCalculator(transactions)
    unrealized = calculator.calculate_unrealized_pnl("AAPL", current_price=105)

    # 成本基准 = (10000 - (-200) + 10) / 100 = 102.1
    # 市值 = 100 * 105 = 10500
    # 未实现盈亏 = 10500 - 10210 = 289.99
    expected_basis = (10000 - (-200) + 10)
    expected_unrealized = 100 * 105 - expected_basis
    print(f"✓ Unrealized PNL Test: {unrealized['unrealized_pnl']} (expected {expected_unrealized})")
    assert abs(unrealized["unrealized_pnl"] - expected_unrealized) < 0.01, \
        f"Expected {expected_unrealized}, got {unrealized['unrealized_pnl']}"


if __name__ == "__main__":
    print("=" * 60)
    print("Running Calculator Fix Tests")
    print("=" * 60)
    
    try:
        test_option_pnl_simple()
        test_adjusted_cost_basis()
        test_realized_pnl()
        test_unrealized_pnl()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
