"""多用户认证：邀请码注册 + 用户名/密码登录。

用 SQLite 做用户表，密码用 PBKDF2 做 hash。故意保持简单、零外部依赖。

数据库文件默认在 <DATA_DIR>/users.db，可通过 AI_HR_DB_FILE 覆盖。
邀请码：若设置环境变量 AI_HR_INVITE_CODES（逗号分隔），每个码只能注册一次；
        若未设置，则只有管理员可以在后台添加邀请码（最简单：启动时
        AI_HR_INVITE_CODES='ABC,DEF' python -m ai_hr.app）。
管理员：AI_HR_ADMIN_USERS 逗号分隔的用户名列表。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import g, jsonify, redirect, request, session, url_for

from . import config

DB_FILE = os.environ.get(
    "AI_HR_DB_FILE", os.path.join(os.path.dirname(config.DATA_FILE), "users.db")
)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

INVITE_CODES_ENV = os.environ.get("AI_HR_INVITE_CODES", "").strip()
ADMIN_USERS = {
    u.strip().lower()
    for u in os.environ.get("AI_HR_ADMIN_USERS", "").split(",")
    if u.strip()
}
DISABLE_SIGNUP = os.environ.get("AI_HR_DISABLE_SIGNUP", "").lower() in (
    "1", "true", "yes",
)

_LOCK = threading.Lock()


# ---------------- DB ----------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with _LOCK, _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                created_at  INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS invites (
                code        TEXT PRIMARY KEY,
                created_at  INTEGER NOT NULL,
                used_by     INTEGER,
                used_at     INTEGER
            )
            """
        )
        # seed invite codes from env if any
        if INVITE_CODES_ENV:
            for code in [c.strip() for c in INVITE_CODES_ENV.split(",") if c.strip()]:
                c.execute(
                    "INSERT OR IGNORE INTO invites(code, created_at) VALUES(?, ?)",
                    (code, int(time.time())),
                )


# ---------------- password hashing (PBKDF2) ----------------

def _hash_password(password: str, salt: Optional[bytes] = None, iters: int = 260000) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return f"pbkdf2_sha256${iters}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# ---------------- user ops ----------------

def _validate_username(username: str) -> Optional[str]:
    if not username or not (3 <= len(username) <= 32):
        return "用户名长度需在 3–32 位"
    if not all(c.isalnum() or c in "_.-" for c in username):
        return "用户名只允许字母、数字、下划线、点、横线"
    return None


def _validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 6:
        return "密码至少 6 位"
    if len(password) > 128:
        return "密码过长"
    return None


def create_user(username: str, password: str, invite_code: str) -> Dict[str, Any]:
    username = (username or "").strip()
    invite_code = (invite_code or "").strip()

    if DISABLE_SIGNUP:
        raise ValueError("注册已关闭")

    err = _validate_username(username) or _validate_password(password)
    if err:
        raise ValueError(err)
    if not invite_code:
        raise ValueError("必须填写邀请码")

    now = int(time.time())
    with _LOCK, _conn() as c:
        row = c.execute(
            "SELECT code, used_by FROM invites WHERE code = ?", (invite_code,)
        ).fetchone()
        if not row:
            raise ValueError("邀请码无效")
        if row["used_by"] is not None:
            raise ValueError("邀请码已被使用")

        if c.execute(
            "SELECT 1 FROM users WHERE lower(username) = lower(?)", (username,)
        ).fetchone():
            raise ValueError("用户名已存在")

        pwd = _hash_password(password)
        cursor = c.execute(
            "INSERT INTO users(username, password, created_at) VALUES(?, ?, ?)",
            (username, pwd, now),
        )
        user_id = cursor.lastrowid
        c.execute(
            "UPDATE invites SET used_by = ?, used_at = ? WHERE code = ?",
            (user_id, now, invite_code),
        )
    return {"id": user_id, "username": username, "created_at": now}


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = (username or "").strip()
    if not username or not password:
        return None
    with _conn() as c:
        row = c.execute(
            "SELECT id, username, password, created_at FROM users WHERE lower(username) = lower(?)",
            (username,),
        ).fetchone()
    if not row:
        return None
    if not _verify_password(password, row["password"]):
        return None
    return {"id": row["id"], "username": row["username"], "created_at": row["created_at"]}


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ---------------- invite codes (admin) ----------------

def generate_invite_code() -> str:
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "").upper()[:12]


def create_invite(code: Optional[str] = None) -> str:
    code = (code or generate_invite_code()).strip().upper()
    with _LOCK, _conn() as c:
        try:
            c.execute(
                "INSERT INTO invites(code, created_at) VALUES(?, ?)",
                (code, int(time.time())),
            )
        except sqlite3.IntegrityError:
            raise ValueError("邀请码已存在")
    return code


def list_invites() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT code, created_at, used_by, used_at FROM invites ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def is_admin(username: Optional[str]) -> bool:
    return bool(username) and username.lower() in ADMIN_USERS


# ---------------- decorators / helpers ----------------

def current_user() -> Optional[Dict[str, Any]]:
    if hasattr(g, "_ai_hr_user"):
        return g._ai_hr_user
    uid = session.get("uid")
    if not uid:
        g._ai_hr_user = None
        return None
    user = get_user(int(uid))
    g._ai_hr_user = user
    return user


def login_user(user: Dict[str, Any]) -> None:
    session.clear()
    session["uid"] = user["id"]
    session["uname"] = user["username"]
    session.permanent = True


def logout_user() -> None:
    session.clear()


def login_required(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录", "code": "unauthenticated"}), 401
            return redirect(url_for("login_page", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录", "code": "unauthenticated"}), 401
            return redirect(url_for("login_page", next=request.path))
        if not is_admin(user["username"]):
            return jsonify({"error": "仅管理员可用"}), 403
        return fn(*args, **kwargs)
    return wrapper
