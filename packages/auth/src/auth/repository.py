"""Session Repository 实现."""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from core.models import Session
from .exceptions import SessionNotFoundError, SessionStorageError


class SessionRepository:
    """SQLite 会话存储仓库."""

    def __init__(self, db_path: str = "./data/auth.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    cookies TEXT NOT NULL DEFAULT '{}',
                    headers TEXT NOT NULL DEFAULT '{}',
                    expires_at TIMESTAMP,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(site, account_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_site_account 
                ON sessions(site, account_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires 
                ON sessions(expires_at)
            """)
            conn.commit()

    def _row_to_session(self, row: tuple) -> Session:
        """将数据库行转换为 Session 对象."""
        return Session(
            session_id=row[0],
            site=row[1],
            account_id=row[2],
            cookies=json.loads(row[3]),
            headers=json.loads(row[4]),
            expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
            metadata=json.loads(row[6]),
        )

    def save(self, session: Session) -> None:
        """保存或更新会话."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sessions 
                    (session_id, site, account_id, cookies, headers, expires_at, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_id) DO UPDATE SET
                        cookies=excluded.cookies,
                        headers=excluded.headers,
                        expires_at=excluded.expires_at,
                        metadata=excluded.metadata,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        session.session_id,
                        session.site,
                        session.account_id,
                        json.dumps(session.cookies),
                        json.dumps(session.headers),
                        session.expires_at.isoformat() if session.expires_at else None,
                        json.dumps(session.metadata),
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to save session: {e}")

    def get_by_session_id(self, session_id: str) -> Optional[Session]:
        """通过会话 ID 获取会话."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                return self._row_to_session(row) if row else None
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to get session: {e}")

    def get_by_account(self, site: str, account_id: str) -> Optional[Session]:
        """通过站点和账号 ID 获取会话."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE site = ? AND account_id = ?", (site, account_id)
                )
                row = cursor.fetchone()
                return self._row_to_session(row) if row else None
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to get session: {e}")

    def delete(self, session_id: str) -> bool:
        """删除会话."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to delete session: {e}")

    def list_by_site(self, site: str) -> List[Session]:
        """列出站点的所有会话."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE site = ? ORDER BY updated_at DESC", (site,)
                )
                return [self._row_to_session(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to list sessions: {e}")

    def purge_expired(self) -> int:
        """清理过期会话，返回删除数量."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE expires_at < ?", (datetime.now().isoformat(),)
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to purge expired sessions: {e}")
