"""
Phase 6 验证 — pages/ 层（适配新 service 接口）

验证项：
1. 导入测试 — pages/ 包正确导出所有页面渲染函数
2. render 函数存在 — 每个页面模块有 render() 函数
3. 依赖方向 — 不导入 FinanceEngine / frontend.config
4. 使用新 ui/ 层 — 从 ui import UI（非 src.components）
5. 使用新 config/ — 从 config 导入常量（非 frontend.config）
6. 文件行数检查 — 每个文件 ≤ 120 行（wheel 特殊允许 ≤ 200）
7. app_v2.py 更新 — 从 pages/ 导入，设置 session_state
"""
import os
import sys
import ast

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

passed = 0
failed = 0


def check(name: str, condition: bool):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        failed += 1


print("=" * 60)
print("Phase 6 验证 — pages/ 层（适配新 service 接口）")
print("=" * 60)


# ── 1. 导入测试 ──
print("\n📦 1. pages 包导入测试")

try:
    from pages import (
        page_overview, page_snapshots, page_yearly,
        page_expense, page_trading, page_wheel,
        page_settings, page_portfolio,
    )
    check("pages/__init__.py 统一导入 8 个页面函数", True)
except Exception as e:
    check(f"pages/__init__.py 统一导入失败 — {e}", False)

# 单独导入各模块
page_modules = [
    ("pages.overview", "render"),
    ("pages.snapshots", "render"),
    ("pages.yearly", "render"),
    ("pages.expense", "render"),
    ("pages.trading", "render"),
    ("pages.wheel", "render"),
    ("pages.settings", "render"),
    ("pages.portfolio.main", "render"),
    ("pages.portfolio.tab_overview", "render"),
    ("pages.portfolio.tab_holdings", "render"),
    ("pages.portfolio.tab_options", "render"),
]

print("\n🔍 2. 各页面模块 render() 函数存在性")

import importlib
for mod_name, func_name in page_modules:
    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, func_name, None)
        check(f"{mod_name}.{func_name} 存在且可调用", callable(fn))
    except Exception as e:
        check(f"{mod_name} 导入失败 — {e}", False)


# ── 3. 依赖方向检查（AST 级别）──
print("\n🚫 3. 依赖方向检查（不导入 FinanceEngine / frontend.config）")

pages_dir = os.path.join(ROOT, "pages")
all_page_files = []

for dirpath, _, filenames in os.walk(pages_dir):
    for fn in sorted(filenames):
        if fn.endswith(".py"):
            all_page_files.append(os.path.join(dirpath, fn))

forbidden_sources = {
    "src.finance_engine": "FinanceEngine（旧入口）",
    "frontend.config": "frontend.config（旧配置）",
}

for fpath in all_page_files:
    relpath = os.path.relpath(fpath, ROOT)
    content = open(fpath, encoding="utf-8").read()

    # 使用 AST 精确检查 import 来源
    try:
        tree = ast.parse(content)
    except SyntaxError:
        check(f"{relpath} 语法正确", False)
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for forbidden, desc in forbidden_sources.items():
                if node.module == forbidden or node.module.startswith(forbidden + "."):
                    check(f"{relpath} 不导入 {desc}", False)
                    break


# 正面检查：没有 forbidden import
for fpath in all_page_files:
    relpath = os.path.relpath(fpath, ROOT)
    content = open(fpath, encoding="utf-8").read()
    has_engine = "from src.finance_engine" in content or "import FinanceEngine" in content
    check(f"{relpath} 不引用 FinanceEngine", not has_engine)

    has_fc = "from frontend.config" in content
    check(f"{relpath} 不引用 frontend.config", not has_fc)


# ── 4. 使用新 ui/ 层 ──
print("\n🎨 4. 使用新 ui/ 层（from ui import ...）")

# 除 settings.py 和 __init__.py 外，其他页面都应该用 UI
ui_pages = [
    "overview.py", "snapshots.py", "yearly.py", "expense.py",
    "trading.py", "wheel.py",
]

for fn in ui_pages:
    fpath = os.path.join(pages_dir, fn)
    content = open(fpath, encoding="utf-8").read()
    uses_new_ui = "from ui import" in content or "from ui " in content
    check(f"{fn} 使用 from ui import", uses_new_ui)

    not_old = "from src.components import" not in content
    check(f"{fn} 不使用 from src.components import", not_old)

# portfolio 子模块
for fn in ["main.py", "tab_overview.py", "tab_holdings.py", "tab_options.py"]:
    fpath = os.path.join(pages_dir, "portfolio", fn)
    content = open(fpath, encoding="utf-8").read()
    uses_new_ui = "from ui import" in content or "from ui " in content
    check(f"portfolio/{fn} 使用 from ui import", uses_new_ui)

    not_old = "from src.components import" not in content
    check(f"portfolio/{fn} 不使用 from src.components import", not_old)


# ── 5. 使用新 services/ 层 ──
print("\n📡 5. 使用新 services/ 层")

service_mapping = {
    "overview.py": "OverviewService",
    "snapshots.py": "SnapshotService",
    "yearly.py": "YearlyService",
    "expense.py": "ExpenseService",
    "trading.py": "TradingService",
    "wheel.py": "WheelService",
}

for fn, svc in service_mapping.items():
    fpath = os.path.join(pages_dir, fn)
    content = open(fpath, encoding="utf-8").read()
    check(f"{fn} 使用 {svc}", svc in content)

# portfolio 使用 PortfolioService
for fn in ["main.py", "tab_overview.py", "tab_holdings.py", "tab_options.py"]:
    fpath = os.path.join(pages_dir, "portfolio", fn)
    content = open(fpath, encoding="utf-8").read()
    if fn != "tab_options.py":
        check(f"portfolio/{fn} 使用 PortfolioService", "PortfolioService" in content)


# ── 6. 使用 config/ 替代 frontend.config ──
print("\n🔧 6. 使用 config/ 包（SSOT）")

# 需要 config 常量的页面
config_pages = [
    ("expense.py", "EXPENSE_SUBCATEGORIES"),
    ("trading.py", "TRADE_ACTION_OPTIONS"),
    ("wheel.py", "COLORS"),
    ("wheel.py", "OPTION_ACTION_LABELS"),
]

for fn, const in config_pages:
    fpath = os.path.join(pages_dir, fn)
    content = open(fpath, encoding="utf-8").read()
    uses_config = f"from config import" in content or f"from config." in content
    check(f"{fn} 从 config 导入 {const}", uses_config and const in content)


# ── 7. 文件行数检查 ──
print("\n📏 7. 文件行数检查")

# 普通页面 ≤ 120 行
normal_limit = 120
# wheel.py 因为渲染子函数多，允许 ≤ 200 行
special_limits = {
    "wheel.py": 200,
    "tab_overview.py": 120,
    "tab_options.py": 120,
}

for fpath in all_page_files:
    fn = os.path.basename(fpath)
    lines = sum(1 for _ in open(fpath, encoding="utf-8"))
    limit = special_limits.get(fn, normal_limit)
    ok = lines <= limit
    check(f"{fn}: {lines} 行 ≤ {limit}" + (" ⚠️ 超限" if not ok else ""), ok)


# ── 8. app_v2.py 更新检查 ──
print("\n🏠 8. app_v2.py 更新检查")

app_path = os.path.join(ROOT, "app_v2.py")
app_content = open(app_path, encoding="utf-8").read()

check("app_v2.py 从 pages 导入", "from pages import" in app_content)
check("app_v2.py 不再从 frontend.page_ 导入",
      "from frontend.page_" not in app_content)
check("app_v2.py 从 config 导入 PAGE_CONFIG",
      "from config import" in app_content and "PAGE_CONFIG" in app_content)
check("app_v2.py 从 config.theme 导入 NAV_CSS",
      "from config.theme import NAV_CSS" in app_content)
check("app_v2.py 设置 session_state.usd_rmb",
      "session_state.usd_rmb" in app_content)
check("app_v2.py 设置 session_state.hkd_rmb",
      "session_state.hkd_rmb" in app_content)
check("app_v2.py 不含内联 _NAV_CSS",
      "_NAV_CSS" not in app_content)

# app_v2.py 行数（应该更短了）
app_lines = sum(1 for _ in open(app_path, encoding="utf-8"))
check(f"app_v2.py: {app_lines} 行 ≤ 80", app_lines <= 80)


# ── 9. pages/__init__.py 导出完整性 ──
print("\n📋 9. pages/__init__.py 导出完整性")

from pages import __all__ as pages_all
expected_exports = [
    "page_overview", "page_snapshots", "page_yearly", "page_expense",
    "page_trading", "page_wheel", "page_settings", "page_portfolio",
]
for name in expected_exports:
    check(f"pages.__all__ 包含 {name}", name in pages_all)


# ═══ 结果 ═══
print("\n" + "=" * 60)
print(f"Phase 6 验证结果: {passed}/{passed + failed} 通过")
if failed:
    print(f"❌ {failed} 项失败")
    sys.exit(1)
else:
    print("✅ 全部通过！pages/ 层适配完成。")
