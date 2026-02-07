## 📦 代码迁移指南

### 🔄 从旧架构到新架构

如果你的代码在使用旧的 `src/calculator.py` 或 `src/models.py`，按照以下步骤迁移到新架构。

---

### ✅ 迁移检查清单

- [ ] 更新所有导入语句
- [ ] 验证测试通过（`python test_calculator_fixes.py`）
- [ ] 检查数据库连接
- [ ] 验证前端应用运行

---

### 📝 导入迁移

#### **旧写法** ❌

```python
from src.calculator import WheelCalculator, PortfolioCalculator
from src.models import Transaction, Campaign, TransactionType
from src.charts import plot_cost_basis_over_time
```

#### **新写法** ✅ (推荐)

```python
# 方式1: 直接从子模块导入 (最清晰)
from src.options import WheelStrategyCalculator
from src.portfolio import PortfolioCalculator, PortfolioAnalyzer
from src.models import Transaction, Campaign, TransactionType
from src.visualization import get_chart_functions

# 方式2: 使用向后兼容层 (过渡期)
from src import WheelCalculator, PortfolioCalculator, Transaction

# 获取图表函数
charts = get_chart_functions()
plot_cost_basis_over_time = charts['plot_cost_basis_over_time']
```

---

### 🔧 函数调用的变化

#### **计算器初始化**

**旧代码**:
```python
from src.calculator import WheelCalculator
calc = WheelCalculator(transactions)
```

**新代码** (兼容):
```python
from src.options import WheelStrategyCalculator as WheelCalculator
calc = WheelCalculator(transactions)
```

---

#### **获取调整成本基准**

代码逻辑完全相同，只需更新导入：

```python
# 调用方式保持不变
basis = calc.calculate_adjusted_cost_basis("AAPL")
print(basis["adjusted_cost"])  # 每股成本
print(basis["cost_basis"])     # 总成本
```

---

#### **期权计算**

**旧代码** (WheelCalculator.calculate_option_pnl):
```python
pnl = calc.calculate_option_pnl("AAPL")
positions = calc.calculate_option_positions("AAPL")
```

**新代码** (通过 WheelStrategyCalculator.option_calc):
```python
# 方式1: 直接使用WheelStrategyCalculator的option_calc
pnl = calc.option_calc.calculate_option_pnl("AAPL")
positions = calc.option_calc.calculate_option_positions("AAPL")

# 方式2: 导入OptionCalculator直接使用
from src.options import OptionCalculator
opt_calc = OptionCalculator(transactions)
pnl = opt_calc.calculate_option_pnl("AAPL")
```

---

### 🎯 新增功能（特色）

新架构中的新功能无需额外代码，直接使用：

```python
from src.portfolio import PortfolioAnalyzer

analyzer = PortfolioAnalyzer(transactions)

# 权利金效率 (新!)
efficiency = analyzer.get_premium_efficiency("AAPL")
print(f"权利金效率: {efficiency['efficiency_pct']}%")

# 多样化分析 (新!)
diversification = analyzer.get_diversification_analysis(prices)
print(diversification['recommendation'])

# 风险分析 (新!)
risk = analyzer.get_risk_metrics(prices)
print(f"风险等级: {risk['risk_level']}")
```

---

### 📊 前端迁移（Streamlit）

#### **旧 app.py**

```python
from src.calculator import WheelCalculator, PortfolioCalculator
from src.models import Transaction

# 手动指定页面布局和图表
```

#### **新 app_v2.py** (推荐)

```python
from src.visualization import PortfolioDashboard

# 使用预制组件，大大简化代码
dashboard = PortfolioDashboard(transactions, prices)
dashboard.render_full_dashboard()
```

**迁移步骤**:

1. 替换 `streamlit run app.py` 为 `streamlit run app_v2.py`
2. 更新导入语句
3. 使用 `PortfolioDashboard` 组件替代手动布局

---

### 🗄️ 数据库迁移

数据库schema 保持不变。仅需注意导入路径：

**旧代码**:
```python
from src.database import init_database, get_transactions
```

**新代码**:
```python
# 目前仍从根目录导入，会逐步迁移
from src.database import init_database, get_transactions
```

---

### ✨ 兼容性表

| 旧位置 | 新位置 | 向后兼容 | 说明 |
|-------|-------|----------|------|
| `src.calculator.WheelCalculator` | `src.options.WheelStrategyCalculator` | ✅ | 别名在 `src/__init__.py` |
| `src.calculator.PortfolioCalculator` | `src.portfolio.PortfolioCalculator` | ✅ | 导出在 `src/__init__.py` |
| `src.models.Transaction` | `src.models.transaction.Transaction` | ✅ | 导出在 `src.models/__init__.py` |
| `src.charts.*` | `src.visualization.charts.*` | ⚠️ | 需要 plotly 安装 |
| `src.database.*` | `src.database.*` | ✅ | 暂未迁移 |

---

### 🧪 验证迁移成功

运行以下命令验证所有导入正确：

```bash
# 测试1: 运行原有测试
python test_calculator_fixes.py

# 测试2: 验证导入
python -c "from src.options import WheelStrategyCalculator; print('✓ 期权模块OK')"
python -c "from src.portfolio import PortfolioCalculator; print('✓ 组合模块OK')"
python -c "from src.visualization import get_chart_functions; print('✓ 可视化模块OK')"

# 测试3: 运行前端
streamlit run app_v2.py
```

---

### 📋 常见问题

**Q: 我能继续使用旧的导入吗?**

A: 是的，向后兼容层会在 `src/__init__.py` 转向新位置。但建议逐步迁移以适应新架构。

**Q: 函数返回值有改变吗?**

A: 没有。所有函数返回值结构保持完全相同，确保兼容性。

**Q: 新架构有性能提升吗?**

A: 性能保持相当。优势在于代码组织和可维护性。

**Q: 如何处理分布在多个文件中的导入?**

A: 使用 `find` 和 `sed` 进行批量替换：

```bash
# 查找所有使用旧导入的文件
grep -r "from src.calculator import" --include="*.py"

# 批量替换（macOS/Linux）
sed -i '' 's/from src.calculator import/from src.options import/g' **/*.py
```

---

### 🚀 迁移完成后

迁移完成后，你可以：

1. **删除旧文件** (可选):
   ```bash
   rm src/calculator.py  # 保留备份！
   ```

2. **更新文档** (推荐):
   - 更新 README.md 中的导入示例
   - 更新团队的开发文档

3. **享受新架构** (开始):
   - 使用新的 PortfolioAnalyzer
   - 使用预制的 PortfolioDashboard
   - 利用更清晰的代码结构进行扩展

---

### 📞 遇到问题?

如果迁移中遇到任何问题：

1. 检查 `ARCHITECTURE.md` 了解新结构
2. 查看 `test_calculator_fixes.py` 的使用示例
3. 运行 `python -c "from src import *; print(dir())"` 查看所有可用的导出
