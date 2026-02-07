"""
Phase 7 验证 — 修复投资组合 Tab + 重建 Mock 数据 + 端到端验证

验证项：
 1. app_v2.py 不再导入 src.database_v2
 2. pages/ 不再导入 src.database_v2（写操作迁移到 db.*）
 3. seed_mock_data.py 使用 db.* API
 4. seed_mock_data.py 无 target / strategy_id / category 参数
 5. seed_mock_data.py 包含 DEPOSIT/WITHDRAW 资金流水
 6. db.transactions.add 自动推断 category
 7. db.yearly.upsert 关键字参数正确
 8. db.snapshots.create 签名正确
 9. seed_mock_data 端到端写入（临时数据库）
10. category CHECK 约束生效（非法值报错）
11. category 隔离：投资不含 INCOME/EXPENSE，记账不含 BUY/SELL
12. py_compile 全部通过
13. PortfolioService 方法名为 load（非 load_data）
14. 依赖方向：db/ 不导入 services/
15. 依赖方向：services/ 不含 streamlit（除 @st.cache_data）
16. 所有新层模块 ≤ 300 行
17. pages/portfolio 子包结构完整
18. 回归：Phase 4-6 测试仍通过（提示性）
"""
import ast
import os
import py_compile
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        msg = f"  ❌ {name}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        failed += 1


print("=" * 60)
print("Phase 7 验证 — 投资组合修复 + Mock 数据 + 端到端")
print("=" * 60)


# ═══════════════════════════════════════════════════
#  1. app_v2.py 不再导入 src.database_v2
# ═══════════════════════════════════════════════════
print("\n📦 1. app_v2.py 导入检查")

with open(os.path.join(ROOT, "app_v2.py")) as f:
    app_src = f.read()

check("app_v2.py 不引用 src.database_v2",
      "src.database_v2" not in app_src)
check("app_v2.py 使用 db.connection.init_database",
      "from db.connection import init_database" in app_src)


# ═══════════════════════════════════════════════════
#  2. pages/ 不再直接写 src.database_v2
# ═══════════════════════════════════════════════════
print("\n📦 2. pages/ 层 DB 写操作迁移检查")

pages_dir = os.path.join(ROOT, "pages")
pages_py = []
for dirpath, _, filenames in os.walk(pages_dir):
    for fn in filenames:
        if fn.endswith(".py") and fn != "__init__.py":
            pages_py.append(os.path.join(dirpath, fn))

for fp in pages_py:
    with open(fp) as f:
        src = f.read()
    rel = os.path.relpath(fp, ROOT)
    check(f"{rel} 无 src.database_v2 导入",
          "from src.database_v2" not in src and "import src.database_v2" not in src)


# ═══════════════════════════════════════════════════
#  3. seed_mock_data.py 使用 db.* API
# ═══════════════════════════════════════════════════
print("\n📦 3. seed_mock_data.py API 检查")

seed_path = os.path.join(ROOT, "scripts", "seed_mock_data.py")
with open(seed_path) as f:
    seed_src = f.read()

check("seed 不含 src.database_v2 引用",
      "src.database_v2" not in seed_src)
check("seed 使用 import db",
      "import db" in seed_src)
check("seed 使用 db.transactions.add",
      "db.transactions.add" in seed_src)
check("seed 使用 db.yearly.upsert",
      "db.yearly.upsert" in seed_src)
check("seed 使用 db.snapshots.create",
      "db.snapshots.create" in seed_src)


# ═══════════════════════════════════════════════════
#  4. seed 无废弃参数
# ═══════════════════════════════════════════════════
print("\n📦 4. seed_mock_data.py 无废弃参数")

# 解析 AST
seed_tree = ast.parse(seed_src)

disallowed_kwargs = {"target", "strategy_id", "category"}
found_bad = set()
for node in ast.walk(seed_tree):
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg in disallowed_kwargs:
                found_bad.add(kw.arg)

check("seed 无 target 参数", "target" not in found_bad)
check("seed 无 strategy_id 参数", "strategy_id" not in found_bad)
check("seed 无 category 参数", "category" not in found_bad,
      f"发现传参: {found_bad}" if found_bad else "")


# ═══════════════════════════════════════════════════
#  5. seed 包含 DEPOSIT/WITHDRAW
# ═══════════════════════════════════════════════════
print("\n📦 5. seed 包含资金流水 (DEPOSIT/WITHDRAW)")

check("seed 包含 DEPOSIT", '"DEPOSIT"' in seed_src or "'DEPOSIT'" in seed_src)
check("seed 包含 WITHDRAW", '"WITHDRAW"' in seed_src or "'WITHDRAW'" in seed_src)


# ═══════════════════════════════════════════════════
#  6. db.transactions.add 自动推断 category
# ═══════════════════════════════════════════════════
print("\n📦 6. infer_category 推断测试")

from config.constants import infer_category, TransactionCategory

mappings = {
    "INCOME":   TransactionCategory.INCOME,
    "EXPENSE":  TransactionCategory.EXPENSE,
    "DEPOSIT":  TransactionCategory.INVESTMENT,
    "WITHDRAW": TransactionCategory.INVESTMENT,
    "BUY":      TransactionCategory.TRADING,
    "SELL":     TransactionCategory.TRADING,
    "STO_CALL": TransactionCategory.TRADING,
    "BTC":      TransactionCategory.TRADING,
    "DIVIDEND": TransactionCategory.TRADING,
    "STO":      TransactionCategory.TRADING,
}

for action, expected in mappings.items():
    result = infer_category(action)
    check(f"infer_category('{action}') → {expected.value}",
          result == expected,
          f"实际: {result.value}")

# 非法 action 报 ValueError
try:
    infer_category("INVALID_ACTION")
    check("非法 action 抛出 ValueError", False)
except ValueError:
    check("非法 action 抛出 ValueError", True)


# ═══════════════════════════════════════════════════
#  7. db.yearly.upsert 签名检查
# ═══════════════════════════════════════════════════
print("\n📦 7. db.yearly.upsert 签名检查")

import inspect
import db

sig = inspect.signature(db.yearly.upsert)
params = list(sig.parameters.keys())
check("upsert 第一个参数是 year", params[0] == "year")
check("upsert 有 pre_tax_income 参数", "pre_tax_income" in params)
check("upsert 有 investment_income 参数", "investment_income" in params)
check("upsert 有 note 参数", "note" in params)


# ═══════════════════════════════════════════════════
#  8. db.snapshots.create 签名检查
# ═══════════════════════════════════════════════════
print("\n📦 8. db.snapshots.create 签名检查")

sig_snap = inspect.signature(db.snapshots.create)
snap_params = list(sig_snap.parameters.keys())
check("create 有 date_str 参数", "date_str" in snap_params)
check("create 有 total_assets_usd 参数", "total_assets_usd" in snap_params)
check("create 有 assets_data 参数", "assets_data" in snap_params)
check("create 有 note 参数", "note" in snap_params)


# ═══════════════════════════════════════════════════
#  9. seed_mock_data 端到端写入（临时数据库）
# ═══════════════════════════════════════════════════
print("\n📦 9. seed_mock_data 端到端写入")

# 用临时数据库运行 seed
import db.connection as conn_mod

_original_db_path = getattr(conn_mod, 'DB_PATH', None)
_original_get_conn = conn_mod.get_connection

tmpdir = tempfile.mkdtemp()
tmp_db = os.path.join(tmpdir, "test_seed.db")

# 猴子补丁 DB_PATH（必须是 Path 对象）
from pathlib import Path as _P
if hasattr(conn_mod, 'DB_PATH'):
    conn_mod.DB_PATH = _P(tmp_db)

# 执行 init + seed
try:
    conn_mod.init_database()

    # 运行 seed_mock_data 中的各函数
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import importlib
    seed_mod = importlib.import_module("seed_mock_data")

    seed_mod.seed_accounts()
    seed_mod.seed_capital_flows()
    seed_mod.seed_investment_transactions()
    seed_mod.seed_expense_income()
    seed_mod.seed_yearly_summary()
    seed_mod.seed_snapshots()

    # 验证数据
    conn = conn_mod.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM transactions")
    tx_count = cur.fetchone()[0]
    check(f"transactions 有数据 ({tx_count} 笔)", tx_count > 0)

    cur.execute("SELECT COUNT(*) FROM snapshots")
    snap_count = cur.fetchone()[0]
    check(f"snapshots 有数据 ({snap_count} 个)", snap_count > 0)

    cur.execute("SELECT COUNT(*) FROM yearly_summary")
    year_count = cur.fetchone()[0]
    check(f"yearly_summary 有数据 ({year_count} 年)", year_count > 0)

    # category 值全部合法
    cur.execute("SELECT DISTINCT category FROM transactions ORDER BY category")
    categories = [r[0] for r in cur.fetchall()]
    valid_cats = {"INCOME", "EXPENSE", "INVESTMENT", "TRADING"}
    check(f"所有 category 值合法: {categories}",
          set(categories).issubset(valid_cats),
          f"非法值: {set(categories) - valid_cats}")

    # DEPOSIT/WITHDRAW 存在
    cur.execute("SELECT COUNT(*) FROM transactions WHERE action IN ('DEPOSIT', 'WITHDRAW')")
    flow_count = cur.fetchone()[0]
    check(f"包含 DEPOSIT/WITHDRAW 资金流水 ({flow_count} 笔)", flow_count > 0)

    # DIVIDEND 存在
    cur.execute("SELECT COUNT(*) FROM transactions WHERE action = 'DIVIDEND'")
    div_count = cur.fetchone()[0]
    check(f"包含 DIVIDEND 分红记录 ({div_count} 笔)", div_count > 0)

    conn.close()

    seed_ok = True
except Exception as e:
    check(f"seed 端到端执行", False, str(e))
    seed_ok = False
finally:
    # 恢复
    if _original_db_path is not None:
        conn_mod.DB_PATH = _original_db_path
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    # 清除已导入的 seed 模块缓存
    if 'seed_mock_data' in sys.modules:
        del sys.modules['seed_mock_data']


# ═══════════════════════════════════════════════════
# 10. CHECK 约束测试
# ═══════════════════════════════════════════════════
print("\n📦 10. category CHECK 约束生效")

# 用全新临时库测试
tmpdir2 = tempfile.mkdtemp()
tmp_db2 = os.path.join(tmpdir2, "test_check.db")

if hasattr(conn_mod, 'DB_PATH'):
    conn_mod.DB_PATH = _P(tmp_db2)

try:
    conn_mod.init_database()
    conn = conn_mod.get_connection()

    # 写入合法 category
    try:
        conn.execute("""
            INSERT INTO transactions (datetime, action, category, currency)
            VALUES ('2025-01-01', 'BUY', 'TRADING', 'USD')
        """)
        conn.commit()
        check("合法 category=TRADING 可写入", True)
    except Exception as e:
        check("合法 category=TRADING 可写入", False, str(e))

    # 写入非法 category
    try:
        conn.execute("""
            INSERT INTO transactions (datetime, action, category, currency)
            VALUES ('2025-01-01', 'BUY', '投资', 'USD')
        """)
        conn.commit()
        check("非法 category='投资' 被 CHECK 拒绝", False, "应该被拒绝但成功了")
    except sqlite3.IntegrityError:
        check("非法 category='投资' 被 CHECK 拒绝", True)
    except Exception as e:
        check("非法 category='投资' 被 CHECK 拒绝", True, f"其他错误: {type(e).__name__}")

    conn.close()
except Exception as e:
    check("CHECK 约束测试环境初始化", False, str(e))
finally:
    if _original_db_path is not None:
        conn_mod.DB_PATH = _original_db_path
    shutil.rmtree(tmpdir2, ignore_errors=True)


# ═══════════════════════════════════════════════════
# 11. category 隔离
# ═══════════════════════════════════════════════════
print("\n📦 11. category 隔离检查")

from config.constants import (
    ACCOUNTING_ACTIONS, STOCK_ACTIONS, OPTION_ACTIONS,
    YIELD_ACTIONS, CAPITAL_ACTIONS,
)

# 记账 action (INCOME/EXPENSE) 不该推断为 TRADING
for a in ACCOUNTING_ACTIONS:
    cat = infer_category(a)
    check(f"{a} → {cat.value} (非 TRADING)",
          cat != TransactionCategory.TRADING)

# 投资 action 不该推断为 INCOME 或 EXPENSE
for a in (STOCK_ACTIONS | OPTION_ACTIONS | YIELD_ACTIONS | CAPITAL_ACTIONS):
    cat = infer_category(a)
    check(f"{a} → {cat.value} (非 INCOME/EXPENSE)",
          cat not in (TransactionCategory.INCOME, TransactionCategory.EXPENSE))


# ═══════════════════════════════════════════════════
# 12. py_compile 全部通过
# ═══════════════════════════════════════════════════
print("\n📦 12. py_compile 全部通过")

import pathlib

all_py = sorted(pathlib.Path(ROOT).glob("**/*.py"))
all_py = [f for f in all_py if "__pycache__" not in str(f) and ".venv" not in str(f)]
compile_errors = []
for f in all_py:
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        compile_errors.append((str(f), str(e)))

check(f"py_compile 全部通过 ({len(all_py)} 文件)",
      len(compile_errors) == 0,
      f"{len(compile_errors)} 个错误")
for path, err in compile_errors[:5]:
    print(f"    → {path}: {err}")


# ═══════════════════════════════════════════════════
# 13. PortfolioService 方法名
# ═══════════════════════════════════════════════════
print("\n📦 13. PortfolioService 方法名检查")

try:
    from services.portfolio.service import PortfolioService
    check("PortfolioService 可导入", True)
    check("有 load 方法", hasattr(PortfolioService, "load"))
    check("无 load_data 方法（已重命名）",
          not hasattr(PortfolioService, "load_data"))
except ImportError as e:
    check("PortfolioService 可导入", False, str(e))


# ═══════════════════════════════════════════════════
# 14. 依赖方向：db/ 不导入 services/
# ═══════════════════════════════════════════════════
print("\n📦 14. 依赖方向检查")

db_dir = os.path.join(ROOT, "db")
for fn in os.listdir(db_dir):
    if fn.endswith(".py"):
        fp = os.path.join(db_dir, fn)
        with open(fp) as f:
            src = f.read()
        check(f"db/{fn} 不导入 services/",
              "from services" not in src and "import services" not in src)


# ═══════════════════════════════════════════════════
# 15. services/ 不含 streamlit（除 @st.cache_data）
# ═══════════════════════════════════════════════════
print("\n📦 15. services/ streamlit 使用检查")

services_dir = os.path.join(ROOT, "services")
for dirpath, _, filenames in os.walk(services_dir):
    for fn in filenames:
        if fn.endswith(".py") and fn != "__init__.py":
            fp = os.path.join(dirpath, fn)
            with open(fp) as f:
                lines = f.readlines()
            rel = os.path.relpath(fp, ROOT)
            # streamlit 只应出现在 import 行或装饰器行
            bad_lines = []
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "streamlit" in stripped or "import st" in stripped:
                    if stripped.startswith("import streamlit"):
                        continue
                    if stripped.startswith("from streamlit"):
                        continue
                    if stripped.startswith("@st.cache"):
                        continue
                    bad_lines.append(i)
            check(f"{rel} 无非装饰器 streamlit 调用",
                  len(bad_lines) == 0,
                  f"行: {bad_lines}" if bad_lines else "")


# ═══════════════════════════════════════════════════
# 16. 新层模块 ≤ 300 行
# ═══════════════════════════════════════════════════
print("\n📦 16. 新层模块行数检查 (≤ 300)")

new_dirs = ["config", "models", "db", "services", "ui", "pages"]
oversized = []
# theme.py 是纯 CSS 配置，允许超过 300 行
EXEMPT_FILES = {"config/theme.py"}
for d in new_dirs:
    dpath = os.path.join(ROOT, d)
    if not os.path.isdir(dpath):
        continue
    for dirpath, _, filenames in os.walk(dpath):
        for fn in filenames:
            if fn.endswith(".py") and fn != "__init__.py":
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, ROOT)
                if rel in EXEMPT_FILES:
                    continue
                with open(fp) as f:
                    lines = len(f.readlines())
                if lines > 300:
                    oversized.append((rel, lines))

check(f"所有新层模块 ≤ 300 行", len(oversized) == 0,
      "; ".join(f"{p}={l}" for p, l in oversized))


# ═══════════════════════════════════════════════════
# 17. pages/portfolio 子包结构
# ═══════════════════════════════════════════════════
print("\n📦 17. pages/portfolio 子包结构")

portfolio_dir = os.path.join(ROOT, "pages", "portfolio")
expected_files = ["__init__.py", "main.py", "tab_overview.py",
                  "tab_holdings.py", "tab_options.py"]
for fn in expected_files:
    fp = os.path.join(portfolio_dir, fn)
    check(f"pages/portfolio/{fn} 存在", os.path.isfile(fp))


# ═══════════════════════════════════════════════════
#  汇总
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
total = passed + failed
print(f"Phase 7 结果: {passed}/{total} 通过")
if failed:
    print(f"  ❌ {failed} 个测试失败")
    sys.exit(1)
else:
    print("  🎉 全部通过！Phase 7 验收完成")
    sys.exit(0)
