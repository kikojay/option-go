"""
Phase 4 验证脚本 — 测试 services/ 层全部导入和基本结构

验证项：
1. 所有 7 个 Service 类可正常导入
2. 每个 Service 的关键方法存在且为 callable
3. 各 Service 声明的 category 范围正确
4. 总行数 < 300 per file（TDD §2.1 规则 #3）
5. 预留接口 (get_net_inflow) 存在
6. 策略注册表 + BaseStrategyCalculator 架构验证
7. WheelCalculator 纯数学方法验证
"""
import os
import sys

# 确保项目根目录在 path 中
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# 模拟 streamlit 缓存装饰器（测试环境无 streamlit）
import types

class FakeStreamlit:
    def cache_data(self, ttl=None, **kw):
        def decorator(fn):
            fn.clear = lambda: None
            return fn
        return decorator

    def cache_resource(self, **kw):
        def decorator(fn):
            fn.clear = lambda: None
            return fn
        return decorator

fake_st = FakeStreamlit()
sys.modules["streamlit"] = types.ModuleType("streamlit")
sys.modules["streamlit"].cache_data = fake_st.cache_data
sys.modules["streamlit"].cache_resource = fake_st.cache_resource

passed = 0
failed = 0

def check(desc, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {desc}")
    else:
        failed += 1
        print(f"  ❌ {desc}")


print("=" * 60)
print("Phase 4 验证 — services/ 层（策略化架构）")
print("=" * 60)

# ── 1. 导入测试 ──
print("\n📦 1. 导入测试")
try:
    from services import (
        OverviewService, SnapshotService, ExpenseService,
        TradingService, YearlyService, PortfolioService, WheelService,
    )
    check("services/__init__.py 统一导入", True)
except Exception as e:
    check(f"services/__init__.py 统一导入 — {e}", False)

try:
    from services.overview import OverviewService
    check("services/overview.py 导入", True)
except Exception as e:
    check(f"services/overview.py 导入 — {e}", False)

try:
    from services.snapshot import SnapshotService
    check("services/snapshot.py 导入", True)
except Exception as e:
    check(f"services/snapshot.py 导入 — {e}", False)

try:
    from services.expense import ExpenseService
    check("services/expense.py 导入", True)
except Exception as e:
    check(f"services/expense.py 导入 — {e}", False)

try:
    from services.trading import TradingService
    check("services/trading.py 导入", True)
except Exception as e:
    check(f"services/trading.py 导入 — {e}", False)

try:
    from services.yearly import YearlyService
    check("services/yearly.py 导入", True)
except Exception as e:
    check(f"services/yearly.py 导入 — {e}", False)

try:
    from services.portfolio import PortfolioService
    check("services/portfolio/ 包导入", True)
except Exception as e:
    check(f"services/portfolio/ 包导入 — {e}", False)

try:
    from services.strategies.wheel import WheelService
    check("services/strategies/wheel/ 包导入", True)
except Exception as e:
    check(f"services/strategies/wheel/ 包导入 — {e}", False)


# ── 2. 方法存在性 ──
print("\n🔍 2. 关键方法存在性")

# OverviewService
check("OverviewService.get_metrics", hasattr(OverviewService, "get_metrics"))
check("OverviewService.get_trend", hasattr(OverviewService, "get_trend"))

# SnapshotService
check("SnapshotService.get_summary", hasattr(SnapshotService, "get_summary"))
check("SnapshotService.get_trend", hasattr(SnapshotService, "get_trend"))
check("SnapshotService.get_detail_rows", hasattr(SnapshotService, "get_detail_rows"))

# ExpenseService
check("ExpenseService.load", hasattr(ExpenseService, "load"))
check("ExpenseService.year_summary", hasattr(ExpenseService, "year_summary"))
check("ExpenseService.monthly_trend", hasattr(ExpenseService, "monthly_trend"))
check("ExpenseService.month_summary", hasattr(ExpenseService, "month_summary"))
check("ExpenseService.category_groups", hasattr(ExpenseService, "category_groups"))
check("ExpenseService.detail", hasattr(ExpenseService, "detail"))

# TradingService
check("TradingService.load", hasattr(TradingService, "load"))
check("TradingService.metrics", hasattr(TradingService, "metrics"))
check("TradingService.detail", hasattr(TradingService, "detail"))

# YearlyService
check("YearlyService.get_data", hasattr(YearlyService, "get_data"))
check("YearlyService.totals", hasattr(YearlyService, "totals"))

# PortfolioService
check("PortfolioService.load", hasattr(PortfolioService, "load"))
check("PortfolioService.calc_overview_metrics", hasattr(PortfolioService, "calc_overview_metrics"))
check("PortfolioService.build_capital_flow_table", hasattr(PortfolioService, "build_capital_flow_table"))
check("PortfolioService.build_trend_data", hasattr(PortfolioService, "build_trend_data"))
check("PortfolioService.build_holdings_rows", hasattr(PortfolioService, "build_holdings_rows"))
check("PortfolioService.calc_holdings_footer", hasattr(PortfolioService, "calc_holdings_footer"))
check("PortfolioService.get_option_symbols", hasattr(PortfolioService, "get_option_symbols"))
check("PortfolioService.get_all_relevant_tx", hasattr(PortfolioService, "get_all_relevant_tx"))
check("PortfolioService.build_options_overview", hasattr(PortfolioService, "build_options_overview"))
check("PortfolioService.build_option_detail", hasattr(PortfolioService, "build_option_detail"))
check("PortfolioService.get_net_inflow (预留)", hasattr(PortfolioService, "get_net_inflow"))

# WheelService
check("WheelService.load", hasattr(WheelService, "load"))
check("WheelService.overview_rows", hasattr(WheelService, "overview_rows"))
check("WheelService.detail_metrics", hasattr(WheelService, "detail_metrics"))
check("WheelService.cost_timeline", hasattr(WheelService, "cost_timeline"))
check("WheelService.trade_details", hasattr(WheelService, "trade_details"))
check("WheelService.recovery", hasattr(WheelService, "recovery"))
check("WheelService.heatmap", hasattr(WheelService, "heatmap"))
check("WheelService.premium_bars", hasattr(WheelService, "premium_bars"))
check("WheelService.action_dist", hasattr(WheelService, "action_dist"))
check("WheelService.option_detail_table", hasattr(WheelService, "option_detail_table"))


# ── 3. staticmethod / callable 验证 ──
print("\n🔧 3. staticmethod 验证")

def is_static_or_decorated(cls, name):
    return callable(getattr(cls, name, None))

for svc_name, methods in [
    ("OverviewService",  ["get_metrics", "get_trend"]),
    ("SnapshotService",  ["get_summary", "get_trend", "get_detail_rows"]),
    ("ExpenseService",   ["load", "year_summary", "monthly_trend", "month_summary", "detail"]),
    ("TradingService",   ["load", "metrics", "detail"]),
    ("YearlyService",    ["get_data", "totals"]),
    ("PortfolioService", ["load", "calc_overview_metrics", "build_holdings_rows"]),
    ("WheelService",     ["load", "overview_rows", "recovery", "heatmap"]),
]:
    cls = eval(svc_name)
    for m in methods:
        check(f"{svc_name}.{m} 可调用", is_static_or_decorated(cls, m))


# ── 4. 文件行数检查（每个 ≤ 300 行） ──
print("\n📏 4. 文件行数检查（每个 ≤ 300 行）")

services_dir = os.path.join(ROOT, "services")

def scan_py_files(base_dir, prefix=""):
    """递归扫描所有 .py 文件"""
    results = []
    for entry in sorted(os.listdir(base_dir)):
        full = os.path.join(base_dir, entry)
        rel = f"{prefix}{entry}" if prefix else entry
        if os.path.isfile(full) and entry.endswith(".py") and entry != "__init__.py":
            results.append((rel, full))
        elif os.path.isdir(full) and not entry.startswith("__"):
            results.extend(scan_py_files(full, prefix=f"{rel}/"))
    return results

for rel_name, fpath in scan_py_files(services_dir):
    lines = sum(1 for _ in open(fpath, encoding="utf-8"))
    ok = lines <= 300
    check(f"{rel_name}: {lines} 行" + (" ⚠️ 超限" if not ok else ""), ok)


# ── 5. Category 范围声明验证 ──
print("\n🎯 5. Category 范围验证")

# ExpenseService
expense_src = open(os.path.join(services_dir, "expense.py"), encoding="utf-8").read()
check("ExpenseService 使用 TransactionCategory.INCOME",
      "TransactionCategory.INCOME" in expense_src)
check("ExpenseService 使用 TransactionCategory.EXPENSE",
      "TransactionCategory.EXPENSE" in expense_src)
check("ExpenseService 不使用 TRADING",
      "TransactionCategory.TRADING" not in expense_src)

# PortfolioService — 读 service.py（主文件）
portfolio_src = open(
    os.path.join(services_dir, "portfolio", "service.py"), encoding="utf-8"
).read()
check("PortfolioService 使用 TransactionCategory.TRADING",
      "TransactionCategory.TRADING" in portfolio_src)
check("PortfolioService 使用 TransactionCategory.INVESTMENT",
      "TransactionCategory.INVESTMENT" in portfolio_src)
check("PortfolioService 不使用 EXPENSE",
      "TransactionCategory.EXPENSE" not in portfolio_src)

# WheelService — 读 strategies/wheel/service.py
wheel_src = open(
    os.path.join(services_dir, "strategies", "wheel", "service.py"),
    encoding="utf-8",
).read()
check("WheelService 使用 TransactionCategory.TRADING",
      "TransactionCategory.TRADING" in wheel_src)
check("WheelService 不使用 INCOME/EXPENSE",
      "TransactionCategory.INCOME" not in wheel_src and
      "TransactionCategory.EXPENSE" not in wheel_src)

# Overview / Snapshot 不直接查 transactions
overview_src = open(os.path.join(services_dir, "overview.py"), encoding="utf-8").read()
check("OverviewService 不直接查 transactions 表",
      "db.transactions" not in overview_src)

snapshot_src = open(os.path.join(services_dir, "snapshot.py"), encoding="utf-8").read()
check("SnapshotService 不直接查 transactions 表",
      "db.transactions" not in snapshot_src)


# ── 6. 预留接口检查 ──
print("\n🔮 6. 预留接口检查")

check("PortfolioService.get_net_inflow 返回字典签名",
      "total_deposited" in portfolio_src and "net_inflow" in portfolio_src)

check("OverviewService.get_metrics 有 fx_mode 参数",
      "fx_mode" in overview_src)


# ── 7. 禁止依赖检查 ──
print("\n🚫 7. 禁止依赖检查（services/ 不应引用 ui/ 或 pages/）")

def check_no_forbidden_imports(base_dir, prefix=""):
    for entry in sorted(os.listdir(base_dir)):
        full = os.path.join(base_dir, entry)
        rel = f"{prefix}{entry}" if prefix else entry
        if os.path.isfile(full) and entry.endswith(".py"):
            content = open(full, encoding="utf-8").read()
            check(f"{rel} 不引用 ui/",
                  "from ui" not in content and "import ui" not in content)
            check(f"{rel} 不引用 pages/",
                  "from pages" not in content and "import pages" not in content)
        elif os.path.isdir(full) and not entry.startswith("__"):
            check_no_forbidden_imports(full, prefix=f"{rel}/")

check_no_forbidden_imports(services_dir)


# ── 8. 策略架构验证 ──
print("\n🏗️ 8. 策略架构验证")

# BaseStrategyCalculator
try:
    from services.strategies.base import BaseStrategyCalculator
    check("BaseStrategyCalculator 导入", True)
    # 验证抽象方法
    import inspect
    abstract_methods = {
        name for name, _ in inspect.getmembers(BaseStrategyCalculator)
        if getattr(getattr(BaseStrategyCalculator, name, None), "__isabstractmethod__", False)
    }
    check("BaseStrategyCalculator 有 get_strategy_symbols",
          "get_strategy_symbols" in abstract_methods)
    check("BaseStrategyCalculator 有 symbol_metrics",
          "symbol_metrics" in abstract_methods)
    # cost_timeline / recovery_prediction 现在是默认实现（非抽象方法）
    check("BaseStrategyCalculator 有 cost_timeline",
          callable(getattr(BaseStrategyCalculator, "cost_timeline", None)))
    check("BaseStrategyCalculator 有 recovery_prediction",
          callable(getattr(BaseStrategyCalculator, "recovery_prediction", None)))
    # 验证新增原子操作
    for m in ("compute_dividends", "compute_stock_cost", "compute_current_shares",
              "compute_option_weeks", "compute_days_held", "annualized_return",
              "weeks_to_zero", "trade_pnl_series"):
        check(f"BaseStrategyCalculator 有 {m}",
              callable(getattr(BaseStrategyCalculator, m, None)))
except Exception as e:
    check(f"BaseStrategyCalculator 导入 — {e}", False)

# WheelCalculator 继承验证
try:
    from services.strategies.wheel.calculator import WheelCalculator
    check("WheelCalculator 导入", True)
    check("WheelCalculator 继承 BaseStrategyCalculator",
          issubclass(WheelCalculator, BaseStrategyCalculator))
    # 验证纯数学方法存在
    check("WheelCalculator.cost_timeline 存在",
          callable(getattr(WheelCalculator, "cost_timeline", None)))
    check("WheelCalculator.trade_pnl_series 存在",
          callable(getattr(WheelCalculator, "trade_pnl_series", None)))
    check("WheelCalculator.recovery_prediction 存在",
          callable(getattr(WheelCalculator, "recovery_prediction", None)))
    check("WheelCalculator.weeks_to_zero 存在",
          callable(getattr(WheelCalculator, "weeks_to_zero", None)))
    check("WheelCalculator.compute_dividends 存在",
          callable(getattr(WheelCalculator, "compute_dividends", None)))
    check("WheelCalculator.compute_stock_cost 存在",
          callable(getattr(WheelCalculator, "compute_stock_cost", None)))
except Exception as e:
    check(f"WheelCalculator 导入 — {e}", False)

# 策略注册表
try:
    from services.strategies import STRATEGY_REGISTRY, get_strategy_service
    check("STRATEGY_REGISTRY 导入", True)
    check("STRATEGY_REGISTRY 包含 wheel",
          "wheel" in STRATEGY_REGISTRY)
    check("get_strategy_service('wheel') 返回 WheelService",
          get_strategy_service("wheel") is WheelService)
except Exception as e:
    check(f"策略注册表 — {e}", False)

# Repair stub 存在
check("strategies/repair/ 目录存在",
      os.path.isdir(os.path.join(services_dir, "strategies", "repair")))


# ── 9. 数据去符号化验证 ──
print("\n💰 9. 数据去符号化验证（Service 不含 $ % 格式化）")

# WheelService.overview_rows 和 trade_details 不应含 $ 格式化
check("WheelService.overview_rows 不含 '$' 格式化",
      "f\"$" not in wheel_src or "overview_rows" not in wheel_src.split("f\"$")[0])

# 检查 wheel service.py 中的 overview_rows 方法体不含 f"$ 模式
# 精确检查：提取 overview_rows 方法源码
ov_start = wheel_src.find("def overview_rows")
ov_end = wheel_src.find("\n    # ─", ov_start + 1) if ov_start >= 0 else -1
if ov_start >= 0 and ov_end >= 0:
    ov_body = wheel_src[ov_start:ov_end]
    check("overview_rows 方法体不含 f'$' 格式化", 'f"$' not in ov_body and "f'$" not in ov_body)
elif ov_start >= 0:
    ov_body = wheel_src[ov_start:]
    check("overview_rows 方法体不含 f'$' 格式化", 'f"$' not in ov_body and "f'$" not in ov_body)

# WheelCalculator 不应依赖 DB 或 UI
calc_src = open(
    os.path.join(services_dir, "strategies", "wheel", "calculator.py"),
    encoding="utf-8",
).read()
check("WheelCalculator 不引用 db 模块",
      "import db" not in calc_src and "from db" not in calc_src)
check("WheelCalculator 不引用 streamlit",
      "import streamlit" not in calc_src and "from streamlit" not in calc_src)
check("WheelCalculator 不引用 api/",
      "from api" not in calc_src and "import api" not in calc_src)


# ── 总结 ──
print("\n" + "=" * 60)
total = passed + failed
print(f"Phase 4 验证结果: {passed}/{total} 通过")
if failed:
    print(f"❌ {failed} 项失败")
    sys.exit(1)
else:
    print("✅ 全部通过！services/ 层策略化架构完成。")
    sys.exit(0)
