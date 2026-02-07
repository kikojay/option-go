"""
数据库模块
"""
# Re-export all functions from the original database module
import importlib
import importlib.util
import sys
from pathlib import Path

# Import the database.py file directly since it's shadowed by this package
_db_file = Path(__file__).parent.parent / "database.py"
_spec = importlib.util.spec_from_file_location("src._database_module", str(_db_file))
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# Re-export all public names
get_connection = _module.get_connection
init_database = _module.init_database
init_default_categories = _module.init_default_categories
add_transaction = _module.add_transaction
get_transactions = _module.get_transactions
create_campaign = _module.create_campaign
get_campaigns = _module.get_campaigns
get_categories_by_type = _module.get_categories_by_type
get_all_accounts = _module.get_all_accounts
update_daily_price = _module.update_daily_price
get_latest_price = _module.get_latest_price
get_portfolio_summary = _module.get_portfolio_summary

__all__ = [
    "get_connection",
    "init_database",
    "init_default_categories",
    "add_transaction",
    "get_transactions",
    "create_campaign",
    "get_campaigns",
    "get_categories_by_type",
    "get_all_accounts",
    "update_daily_price",
    "get_latest_price",
    "get_portfolio_summary",
]
