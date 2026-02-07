"""设置页面 — 数据备份与数据库信息"""
import streamlit as st

from db.connection import get_db_path
from ui import UI


def render():
    UI.inject_css()
    UI.header("设置", "Settings")

    UI.sub_heading("数据备份")
    st.code(
        "scp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/"
        "option-go/data/*.db ~/Documents/Backup/",
        language="bash")

    UI.sub_heading("数据库信息")
    db_path = get_db_path()
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        st.info(f"数据库路径: `{db_path}`\n\n大小: {size_kb:.1f} KB")
    else:
        st.warning("数据库文件不存在")
