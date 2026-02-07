"""页面：设置 Settings"""
import streamlit as st
from pathlib import Path


def page_settings():
    st.title("⚙️ 设置")

    st.subheader("💾 数据备份")
    st.code(
        "scp -P 12628 root@185.183.84.67:/root/.openclaw/workspace/code/option-go/data/*.db ~/Documents/Backup/",
        language="bash",
    )

    st.subheader("🗄️ 数据库信息")
    db_path = Path(__file__).parent.parent / "data" / "wealth_v2.db"
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        st.info(f"数据库路径: `{db_path}`\n\n大小: {size_kb:.1f} KB")
    else:
        st.warning("数据库文件不存在")
