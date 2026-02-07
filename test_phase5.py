"""
Phase 5 验证 — ui/ 层（UI 组件库重整）

验证项：
1. 导入测试 — ui/ 包正确导出 UI、plotly_layout 等
2. 关键方法存在性 — UI 类的全部静态方法
3. 依赖方向 — ui/ 只依赖 config/ + streamlit，不引用 frontend/pages/services/
4. 反向依赖解除 — ui/ 不 import frontend/
5. 向后兼容 — src/components.py 仍可导入 UI
6. 文件行数 — 每个文件 ≤ 300 行
7. config SSOT — ui/ 使用 config/theme.py 的颜色和 CSS
"""
import os
import sys
import inspect

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
print("Phase 5 验证 — ui/ 层（UI 组件库重整）")
print("=" * 60)


# ── 1. 导入测试 ──
print("\n📦 1. 导入测试")

try:
    from ui import UI, plotly_layout, render_chart, color_for_value
    check("ui/__init__.py 统一导入", True)
except Exception as e:
    check(f"ui/__init__.py 统一导入 — {e}", False)

try:
    from ui.components import UI as UI2
    check("ui/components.py 导入", True)
except Exception as e:
    check(f"ui/components.py 导入 — {e}", False)

try:
    from ui.charts import plotly_layout as pl2, render_chart as rc2
    check("ui/charts.py 导入", True)
except Exception as e:
    check(f"ui/charts.py 导入 — {e}", False)


# ── 2. UI 关键方法存在性 ──
print("\n🔍 2. UI 关键方法存在性")

UI_METHODS = [
    "inject_css", "card", "metric_row", "header", "sub_heading",
    "list_item", "divider", "footer", "table", "progress_bar",
    "empty", "pnl_color", "pnl_text",
]

for method_name in UI_METHODS:
    attr = getattr(UI, method_name, None)
    check(f"UI.{method_name}", callable(attr))


# ── 3. charts 方法存在性 ──
print("\n📊 3. charts 方法存在性")

check("plotly_layout 可调用", callable(plotly_layout))
check("render_chart 可调用", callable(render_chart))
check("color_for_value 可调用", callable(color_for_value))

# plotly_layout 返回 dict
result = plotly_layout(height=400)
check("plotly_layout 返回 dict", isinstance(result, dict))
check("plotly_layout 含 height override", result.get("height") == 400)
check("plotly_layout 含 template", "template" in result)

# color_for_value 正确返回
from config.theme import COLORS
check("color_for_value(100) = gain 色", color_for_value(100) == COLORS["gain"])
check("color_for_value(-50) = loss 色", color_for_value(-50) == COLORS["loss"])


# ── 4. 依赖方向检查 ──
print("\n🚫 4. 依赖方向检查（ui/ 不应引用 frontend/pages/services/）")

ui_dir = os.path.join(ROOT, "ui")
forbidden_imports = ["frontend", "pages/", "services/"]

for entry in sorted(os.listdir(ui_dir)):
    if not entry.endswith(".py"):
        continue
    fpath = os.path.join(ui_dir, entry)
    content = open(fpath, encoding="utf-8").read()
    for dep in forbidden_imports:
        check(f"{entry} 不引用 {dep}",
              f"from {dep}" not in content and f"import {dep}" not in content)


# ── 5. 反向依赖解除验证 ──
print("\n🔗 5. 反向依赖解除")

# ui/components.py 不 import frontend/config
ui_comp_src = open(os.path.join(ui_dir, "components.py"), encoding="utf-8").read()
check("ui/components.py 不 import frontend.config",
      "from frontend" not in ui_comp_src and "import frontend" not in ui_comp_src)

# ui/components.py 使用 config.theme
check("ui/components.py 使用 config.theme",
      "from config.theme import" in ui_comp_src or "from config import" in ui_comp_src)

# ui/charts.py 使用 config.theme
ui_charts_src = open(os.path.join(ui_dir, "charts.py"), encoding="utf-8").read()
check("ui/charts.py 使用 config.theme",
      "from config.theme import" in ui_charts_src or "from config import" in ui_charts_src)


# ── 6. 向后兼容 shim ──
print("\n🔄 6. 向后兼容 shim")

try:
    from src.components import UI as UILegacy
    check("src.components.UI 向后兼容导入", True)
    check("src.components.UI 指向 ui.components.UI", UILegacy is UI)
except Exception as e:
    check(f"src.components 向后兼容 — {e}", False)

# src/components.py 是 shim，行数极少
src_comp_path = os.path.join(ROOT, "src", "components.py")
src_comp_lines = sum(1 for _ in open(src_comp_path, encoding="utf-8"))
check(f"src/components.py 是 shim（{src_comp_lines} 行 ≤ 15）", src_comp_lines <= 15)


# ── 7. 文件行数检查 ──
print("\n📏 7. 文件行数检查（每个 ≤ 300 行）")

for entry in sorted(os.listdir(ui_dir)):
    if not entry.endswith(".py") or entry == "__init__.py":
        continue
    fpath = os.path.join(ui_dir, entry)
    lines = sum(1 for _ in open(fpath, encoding="utf-8"))
    ok = lines <= 300
    check(f"{entry}: {lines} 行" + (" ⚠️ 超限" if not ok else ""), ok)


# ── 8. SSOT 验证 — ui/ 使用 config/theme 的 COLORS ──
print("\n🎨 8. SSOT 验证（UI 使用 config/theme.py 的 COLORS）")

# 检查 ui/components.py 没有自己定义 COLORS 字典
comp_lines = open(os.path.join(ui_dir, "components.py"), encoding="utf-8").readlines()
has_own_colors = any(
    line.strip().startswith("COLORS") and "=" in line and "{" in line
    for line in comp_lines
)
check("ui/components.py 不重复定义 COLORS dict", not has_own_colors)

# charts.py 没有自己定义 PLOTLY_LAYOUT_DEFAULTS
chart_lines = open(os.path.join(ui_dir, "charts.py"), encoding="utf-8").readlines()
has_own_layout = any(
    "PLOTLY_LAYOUT_DEFAULTS" in line and "=" in line and "{" in line
    for line in chart_lines
)
check("ui/charts.py 不重复定义 PLOTLY_LAYOUT_DEFAULTS", not has_own_layout)


# ── 9. config/theme.py 完整性 ──
print("\n🏗️ 9. config/theme.py 完整性")

from config.theme import COLORS as THEME_COLORS, GLOBAL_CSS, MOBILE_CSS, PLOTLY_LAYOUT_DEFAULTS
check("COLORS 包含 gain", "gain" in THEME_COLORS)
check("COLORS 包含 loss", "loss" in THEME_COLORS)
check("COLORS 包含 text", "text" in THEME_COLORS)
check("COLORS 包含 text_muted", "text_muted" in THEME_COLORS)
check("COLORS 包含 primary", "primary" in THEME_COLORS)
check("COLORS 包含 accent", "accent" in THEME_COLORS)
check("GLOBAL_CSS 非空", len(GLOBAL_CSS) > 100)
check("MOBILE_CSS 非空", len(MOBILE_CSS) > 100)
check("PLOTLY_LAYOUT_DEFAULTS 非空", len(PLOTLY_LAYOUT_DEFAULTS) > 3)


# ── 10. UI 方法均为 staticmethod ──
print("\n🔧 10. UI 方法均为 staticmethod")

for method_name in UI_METHODS:
    is_static = isinstance(inspect.getattr_static(UI, method_name), staticmethod)
    check(f"UI.{method_name} 是 staticmethod", is_static)


# ═══ 结果 ═══
print("\n" + "=" * 60)
print(f"Phase 5 验证结果: {passed}/{passed + failed} 通过")
if failed:
    print(f"❌ {failed} 项失败")
    sys.exit(1)
else:
    print("✅ 全部通过！ui/ 层重整完成。")
