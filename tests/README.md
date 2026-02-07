# 测试说明

- 运行：`pytest -q`
- 测试固定使用 shadow 数据库：`data/wealth_test.db`
- prod / shadow 分区：
	- prod: `data/wealth.db`
	- shadow: `data/wealth_test.db`
- 一键从 prod 同步到 shadow：
	- `python -c "from db.connection import sync_shadow_from_prod; sync_shadow_from_prod()"`

- 容错回归测试：`tests/services/resilience_spec.py`
