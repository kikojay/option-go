"""
资产快照 CRUD

每月一条快照，记录该月的资产全貌。
"""
import json
from typing import Optional, List, Dict, Any

from db.connection import get_connection


def create(
    date_str: str,
    total_assets_usd: float,
    total_assets_rmb: float,
    assets_data: Dict[str, Any],
    *,
    note: Optional[str] = None,
) -> int:
    """
    创建资产快照

    Args:
        date_str:         日期 (YYYY-MM-DD)
        total_assets_usd: 总资产（美元）
        total_assets_rmb: 总资产（人民币）
        assets_data:      分项资产明细（dict → JSON 存储）
        note:             备注

    Returns:
        新快照的 ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO snapshots (date, total_assets_usd, total_assets_rmb, assets_json, note)
        VALUES (?, ?, ?, ?, ?)
    """, (
        date_str, total_assets_usd, total_assets_rmb,
        json.dumps(assets_data, ensure_ascii=False), note,
    ))
    snap_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return snap_id


def get_latest() -> Optional[Dict[str, Any]]:
    """获取最新快照（按日期倒序取第一条）"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM snapshots ORDER BY date DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return _parse_row(row) if row else None


def get_all() -> List[Dict[str, Any]]:
    """获取所有快照（按日期倒序）"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM snapshots ORDER BY date DESC"
    ).fetchall()
    conn.close()
    return [_parse_row(r) for r in rows]


def get_by_id(snap_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取快照"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM snapshots WHERE id = ?", (snap_id,)
    ).fetchone()
    conn.close()
    return _parse_row(row) if row else None


def delete(snap_id: int) -> bool:
    """删除快照"""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM snapshots WHERE id = ?", (snap_id,)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update(snap_id: int, **fields) -> bool:
    """
    更新快照的指定字段

    如果包含 assets_data (dict)，自动序列化为 JSON。
    """
    if not fields:
        return False

    # 自动序列化 assets_data → assets_json
    if "assets_data" in fields:
        fields["assets_json"] = json.dumps(
            fields.pop("assets_data"), ensure_ascii=False
        )

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [snap_id]

    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE snapshots SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def _parse_row(row) -> Dict[str, Any]:
    """解析快照行：JSON 字段反序列化"""
    data = dict(row)
    raw = data.get("assets_json")
    data["assets_data"] = json.loads(raw) if raw else {}
    return data
