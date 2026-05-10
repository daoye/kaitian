"""下载记录 SQLite 持久化。

以站点为维度记录下载进度，每个站点下管理多个 URL。
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from core.exceptions import KaitianError
from core.models import Workflow
from core.types import WorkflowStatus, WorkflowStep


class InvalidStepError(KaitianError):
    """使用了无效的步骤名称。"""
    pass


class SiteRepository:
    """站点下载记录仓库。

    以站点为维度组织记录。每个站点下管理多个 URL 的下载进度。
    URL 在同一站点内唯一。
    """

    def __init__(self, db_path: str = "./data/kaitian.db"):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS site_records (
                    id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    name TEXT,
                    step TEXT NOT NULL DEFAULT 'initial',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_site_records_site
                    ON site_records(site);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_site_records_url
                    ON site_records(site, source_url);
            """)
            conn.commit()
        finally:
            conn.close()

    def set(
        self,
        site: str,
        source_url: str,
        step: str = "pending",
        name: str | None = None,
        status: str = "running",
    ) -> Workflow:
        """在指定站点下记录或更新一个 URL 的下载进度。同站点同 URL 自动更新。

        Raises:
            InvalidStepError: step 不在预定义列表中
        """
        self._validate_step(step)
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM site_records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE site_records SET step=?, status=?, name=COALESCE(?,name), updated_at=? WHERE site=? AND source_url=?",
                    (step, status, name, now, site, source_url),
                )
            else:
                conn.execute(
                    "INSERT INTO site_records (id, site, source_url, name, step, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex[:16], site, source_url, name, step, status, now, now),
                )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM site_records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            return self._row_to_workflow(row)
        finally:
            conn.close()

    def get(self, site: str, source_url: str) -> Workflow | None:
        """查询指定站点下某个 URL 的进度。"""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM site_records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            return self._row_to_workflow(row) if row else None
        finally:
            conn.close()

    def list(self, site: str, status: str | None = None, limit: int = 200) -> list[Workflow]:
        """列出指定站点下的所有 URL 记录。"""
        conn = self._connect()
        try:
            query = "SELECT * FROM site_records WHERE site = ?"
            params: list[Any] = [site]
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_workflow(r) for r in rows]
        finally:
            conn.close()

    def status(self, site: str) -> dict:
        """返回指定站点的汇总统计。"""
        conn = self._connect()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM site_records WHERE site = ?", (site,)
            ).fetchone()["cnt"]
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM site_records WHERE site = ? GROUP BY status",
                (site,),
            ).fetchall()
            counts = {r["status"]: r["cnt"] for r in rows}
            return {
                "site": site,
                "total": total,
                "completed": counts.get("completed", 0),
                "running": counts.get("running", 0),
                "failed": counts.get("failed", 0),
                "pending": counts.get("pending", 0),
            }
        finally:
            conn.close()

    def done(self, site: str, source_url: str) -> Workflow | None:
        """标记指定站点下某 URL 为已完成。"""
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE site_records SET step='completed', status='completed', updated_at=? WHERE site=? AND source_url=?",
                (now, site, source_url),
            )
            conn.commit()
            return self.get(site, source_url)
        finally:
            conn.close()

    def fail(self, site: str, source_url: str, step: str) -> Workflow | None:
        """标记指定站点下某 URL 为失败。"""
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE site_records SET step=?, status='failed', updated_at=? WHERE site=? AND source_url=?",
                (step, now, site, source_url),
            )
            conn.commit()
            return self.get(site, source_url)
        finally:
            conn.close()

    def remove(self, site: str, source_url: str) -> bool:
        """删除指定站点下某 URL 的记录。"""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM site_records WHERE site = ? AND source_url = ?",
                (site, source_url),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_sites(self) -> list[dict]:
        """列出所有有记录的站点及统计。"""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT site,
                       COUNT(*) as total,
                       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) as running,
                       SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
                FROM site_records
                GROUP BY site
                ORDER BY total DESC
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _validate_step(self, step: str) -> None:
        if step in ("completed", "failed"):
            return  # done/fail 命令使用，允许
        try:
            WorkflowStep(step)
        except ValueError:
            valid = WorkflowStep.valid_steps()
            raise InvalidStepError(
                f"无效步骤 '{step}'，有效值: {', '.join(valid)}"
            ) from None

    def _row_to_workflow(self, row: sqlite3.Row) -> Workflow:
        return Workflow(
            id=row["id"],
            source=row["site"],
            source_url=row["source_url"],
            name=row["name"],
            step=WorkflowStep(row["step"]),
            status=WorkflowStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
