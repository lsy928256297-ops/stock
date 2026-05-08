"""候选人行数据的持久化：使用简单的 JSON 文件。

数据结构（单行 = 一位候选人）:
{
  "id": "uuid",
  "owner": <user_id|null>,         # 多用户模式下每行归属某用户；null 表示旧数据
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "job_desc": "...",
  "resume_filename": "...",
  "resume_text": "...",
  "focus_points": "...",
  "questions_md": "...",
  "interview_notes": "...",
  "analysis": { ... JSON from LLM ... }
}
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Dict, List, Optional

from . import config

_LOCK = threading.Lock()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _load_all() -> List[Dict]:
    if not os.path.exists(config.DATA_FILE):
        return []
    try:
        with open(config.DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        return []
    return []


def _save_all(rows: List[Dict]) -> None:
    tmp = config.DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.DATA_FILE)


def _matches_owner(row: Dict, owner: Optional[int]) -> bool:
    """owner=None 表示不过滤（单机模式 / 兼容老数据）。"""
    if owner is None:
        return True
    return row.get("owner") == owner


def list_rows(owner: Optional[int] = None) -> List[Dict]:
    with _LOCK:
        rows = _load_all()
    return [r for r in rows if _matches_owner(r, owner)]


def get_row(row_id: str, owner: Optional[int] = None) -> Optional[Dict]:
    with _LOCK:
        for row in _load_all():
            if row.get("id") == row_id and _matches_owner(row, owner):
                return row
    return None


def create_row(owner: Optional[int] = None, **fields) -> Dict:
    row = {
        "id": str(uuid.uuid4()),
        "owner": owner,
        "created_at": _now(),
        "updated_at": _now(),
        "job_desc": "",
        "resume_filename": "",
        "resume_text": "",
        "focus_points": "",
        "questions_md": "",
        "interview_notes": "",
        "analysis": None,
    }
    row.update({k: v for k, v in fields.items() if v is not None})
    with _LOCK:
        rows = _load_all()
        rows.append(row)
        _save_all(rows)
    return row


def update_row(row_id: str, owner: Optional[int] = None, **fields) -> Optional[Dict]:
    with _LOCK:
        rows = _load_all()
        for row in rows:
            if row.get("id") == row_id and _matches_owner(row, owner):
                for k, v in fields.items():
                    if v is not None:
                        row[k] = v
                row["updated_at"] = _now()
                _save_all(rows)
                return row
    return None


def delete_row(row_id: str, owner: Optional[int] = None) -> bool:
    with _LOCK:
        rows = _load_all()
        new_rows = [
            r for r in rows
            if not (r.get("id") == row_id and _matches_owner(r, owner))
        ]
        if len(new_rows) == len(rows):
            return False
        _save_all(new_rows)
        return True
