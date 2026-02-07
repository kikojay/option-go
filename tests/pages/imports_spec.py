"""页面模块导入与 render 存在性检查。"""
from __future__ import annotations

import importlib


def _assert_render(module_path: str) -> None:
    mod = importlib.import_module(module_path)
    assert hasattr(mod, "render")
    assert callable(getattr(mod, "render"))


def test_pages_assets_imports():
    """资产追踪页面可导入。"""
    _assert_render("pages.assets.overview")
    _assert_render("pages.assets.snapshots")
    _assert_render("pages.assets.yearly")


def test_pages_accounting_imports():
    """日常记账页面可导入。"""
    _assert_render("pages.accounting.expense")


def test_pages_investing_imports():
    """投资监控页面可导入。"""
    _assert_render("pages.investing.trading")
    _assert_render("pages.investing.wheel")
    _assert_render("pages.investing.portfolio.main")
    _assert_render("pages.investing.portfolio.tab_overview")
    _assert_render("pages.investing.portfolio.tab_holdings")
    _assert_render("pages.investing.portfolio.tab_options")


def test_pages_settings_imports():
    """设置页面可导入。"""
    _assert_render("pages.settings")
