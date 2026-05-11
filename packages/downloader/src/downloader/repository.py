"""任务记录 SQLite 持久化。

通用工作流记录，支持下载、上传、发布等场景。
以 (site, source_url) 为唯一键管理任务进度。
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


class RecordRepository:
    """通用任务记录仓库。

    以 (site, source_url) 为唯一键管理任意工作流进度。
    site 标识任务类型/目标平台（如 "3dbrute.com", "znzmo"）。
    source_url 标识具体任务对象（如下载 URL、本地目录路径）。
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
            conn.executescript(f"""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    name TEXT,
                    step TEXT NOT NULL DEFAULT '{WorkflowStep.PENDING}',
                    status TEXT NOT NULL DEFAULT '{WorkflowStatus.PENDING}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_records_site
                    ON records(site);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_records_url
                    ON records(site, source_url);
            """)
            conn.commit()
        finally:
            conn.close()

    def set(
        self,
        site: str,
        source_url: str,
        step: WorkflowStep | str = WorkflowStep.PENDING,
        name: str | None = None,
        status: WorkflowStatus | str = WorkflowStatus.RUNNING,
    ) -> Workflow:
        """记录或更新任务进度。同 site + source_url 自动更新。

        Raises:
            InvalidStepError: step 不在预定义列表中
        """
        self._validate_step(step)
        step_str = step.value if isinstance(step, WorkflowStep) else step
        status_str = status.value if isinstance(status, WorkflowStatus) else status
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE records SET step=?, status=?, name=COALESCE(?,name), updated_at=? WHERE site=? AND source_url=?",
                    (step_str, status_str, name, now, site, source_url),
                )
            else:
                conn.execute(
                    "INSERT INTO records (id, site, source_url, name, step, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex[:16], site, source_url, name, step_str, status_str, now, now),
                )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            return self._row_to_workflow(row)
        finally:
            conn.close()

    def get(self, site: str, source_url: str) -> Workflow | None:
        """查询指定任务的进度。"""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM records WHERE site = ? AND source_url = ?",
                (site, source_url),
            ).fetchone()
            return self._row_to_workflow(row) if row else None
        finally:
            conn.close()

    def is_completed(self, site: str, source_url: str) -> bool:
        """检查任务是否已完成。"""
        record = self.get(site, source_url)
        return record is not None and record.status == WorkflowStatus.COMPLETED

    def list(self, site: str, status: str | None = None, limit: int = 200) -> list[Workflow]:
        """列出指定 site 下的所有任务记录。"""
        conn = self._connect()
        try:
            query = "SELECT * FROM records WHERE site = ?"
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
        """返回指定 site 的任务汇总统计。"""
        conn = self._connect()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM records WHERE site = ?", (site,)
            ).fetchone()["cnt"]
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM records WHERE site = ? GROUP BY status",
                (site,),
            ).fetchall()
            counts = {r["status"]: r["cnt"] for r in rows}
            return {
                "site": site,
                "total": total,
                "completed": counts.get(WorkflowStatus.COMPLETED, 0),
                "running": counts.get(WorkflowStatus.RUNNING, 0),
                "failed": counts.get(WorkflowStatus.FAILED, 0),
                "pending": counts.get(WorkflowStatus.PENDING, 0),
            }
        finally:
            conn.close()

    def done(self, site: str, source_url: str) -> Workflow | None:
        """标记任务为已完成。"""
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE records SET step=?, status=?, updated_at=? WHERE site=? AND source_url=?",
                (WorkflowStep.COMPLETED.value, WorkflowStatus.COMPLETED.value, now, site, source_url),
            )
            conn.commit()
            return self.get(site, source_url)
        finally:
            conn.close()

    def fail(self, site: str, source_url: str, step: WorkflowStep) -> Workflow | None:
        """标记任务为失败。"""
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE records SET step=?, status=?, updated_at=? WHERE site=? AND source_url=?",
                (step.value, WorkflowStatus.FAILED.value, now, site, source_url),
            )
            conn.commit()
            return self.get(site, source_url)
        finally:
            conn.close()

    def remove(self, site: str, source_url: str) -> bool:
        """删除指定任务记录。"""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM records WHERE site = ? AND source_url = ?",
                (site, source_url),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_sites(self) -> list[dict]:
        """列出所有有记录的 site 及统计。"""
        conn = self._connect()
        try:
            rows = conn.execute(f"""
                SELECT site,
                       COUNT(*) as total,
                       SUM(CASE WHEN status=? THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status=? THEN 1 ELSE 0 END) as running,
                       SUM(CASE WHEN status=? THEN 1 ELSE 0 END) as failed
                FROM records
                GROUP BY site
                ORDER BY total DESC
            """, (WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING, WorkflowStatus.FAILED)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _validate_step(self, step: WorkflowStep | str) -> None:
        if isinstance(step, WorkflowStep):
            return
        try:
            WorkflowStep(step)
        except ValueError:
            valid = [s.value for s in WorkflowStep]
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



