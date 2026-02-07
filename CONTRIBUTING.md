# Wealth Tracker 开发者规范 (CONTRIBUTING)

> 核心原则：各司其职、单向依赖、自底向上验证。

## 1. 架构分层契约 (Layered Contract)

为了防止 KeyError 和逻辑混乱，必须严格遵守数据流向准则：

### 数据层 (db/)
- 返回原始 dict 或 sqlite3.Row。
- 不做业务计算，不做格式化。
- 只负责 CRUD。

### 服务层 (services/)
- 输入：接受原始数据。
- 处理：调用 Calculators 执行金融运算。
- 输出：返回全小写英文 Key 的 TypedDict 或 list[dict]（如 cost_basis, net_pnl）。
- 禁止：严禁在 Service 层进行 $ / ¥ / % 字符串拼接，严禁使用中文作为 Key。

### 视图层 (pages/)
- 职责：负责 UI 编排。
- 渲染：仅在渲染那一刻通过 UI 组件将数字转换为格式化字符串。

## 2. 目录职责与依赖约束

允许依赖：
- pages/ -> services/ + ui/ + config/
- services/ -> db/ + api/ + config/ + utils/ + calculators/
- ui/ -> config/
- db/ -> config/ (只用于常量)

禁止依赖：
- services/ -> ui/
- db/ -> services/ 或 pages/
- 任何层 -> pages/

## 3. 命名规范

- Service 输出的 Key 一律英文小写下划线。
- UI 侧展示的列名与标题可使用中文。
- 常量统一放在 config/ 中，避免散落各处。

## 4. 缓存规范

- 读操作可用 @st.cache_data，写操作后必须清缓存。
- 写入后的清缓存必须写在 UI 触发回调中（比如按钮提交后）。

## 5. 数据分区与测试数据库

- 数据库分区：
  - prod: `data/wealth.db`
  - shadow: `data/wealth_test.db`
- 测试只能改 shadow，禁止写 prod。
- 通过环境变量控制：
  - `WEALTH_DB_ROLE=shadow` 强制使用 shadow。
  - `WEALTH_DB_PATH=/abs/path/xxx.db` 可自定义路径。
- 一键从 prod 同步到 shadow：
  - `python -c "from db.connection import sync_shadow_from_prod; sync_shadow_from_prod()"`

## 6. 自动化诊断协议 (Diagnostic Protocol)

当页面出现崩溃或显示异常时，必须按以下顺序进行 Debug：

### Phase 1: 逻辑层隔离验证 (Isolated Logic Test)
- 不启动 Streamlit，直接运行测试脚本：
  - 实例化对应的 Service。
  - 调用核心加载方法（如 PortfolioService.load()）。
  - 断言校验：核对返回值的 Key 是否与 View 层代码一致。

### Phase 2: 渲染安全校验 (UI Safety Check)
- 禁止 HTML 注入标题：所有 st.expander、st.tabs 和 st.button 的 Label 必须为纯文本。
- 样式封装：所有 CSS 注入必须由 ui/components.py 统一管理，严禁在 pages/ 下手动编写 HTML 标签。

### Phase 3: 状态追踪 (State Tracking)
- 确保 st.session_state 在 app.py 中已初始化。
- 检查 @st.cache_data 是否在写操作后被执行了 .clear()。

## 7. 期权策略扩展规范 (Strategy Extension)

如果要增加新策略（如 Stock Repair）：
- Calculator：在 calculators/ 下新建纯数学类，计算 Breakeven 和收益率。
- Service：在 services/investing/strategies/ 下新建目录，封装业务逻辑。
- UI：复用 ui/components.py 中的标准卡片。

## 8. 模块自检清单

- assets/overview: 账户余额存在，快照可读，图表能渲染。
- assets/snapshots: 自动/手动快照可生成，历史明细无报错。
- assets/yearly: 年度表与图表一致。
- accounting/expense: 统计口径正确，分类图无缺失列。
- investing/trading: 交易明细含金额换算，手续费可解释。
- investing/portfolio: 三个 Tab 均可加载。
- investing/wheel: 策略标的可识别，回本预测不崩。
- settings: 数据库路径与实际一致。

## 9. 常见问题排查

- 总览显示 0：检查 accounts 表是否为空。
- 乱码图标：检查全局字体 CSS 是否覆盖 Material 图标字体。
- 数据不更新：检查 cache clear 是否遗漏。

## 10. 最小测试建议

- services/ 的核心 load() 方法必须有单测。
- 每个页面至少覆盖 1 条 happy path + 1 条空数据路径。
- 必须包含空库/缺失数据的容错回归测试。

## 11. 测试命名与结构

- 测试文件按 prod 结构镜像组织：
  - `tests/services/assets_spec.py`
  - `tests/services/accounting_spec.py`
  - `tests/services/investing_spec.py`
  - `tests/services/resilience_spec.py`
  - `tests/pages/imports_spec.py`
- 命名使用 `_spec.py` 后缀，不使用 `test_` 前缀。
