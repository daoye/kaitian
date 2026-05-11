"""知末批量上传编排器 — 支持 batch 和 daemon 模式。

扫描本地模型目录，自动过滤已上传成功的模型，调度上传。
"""

import asyncio
import logging
import time
from pathlib import Path

from core.config import get_config
from core.types import WorkflowStatus, WorkflowStep
from downloader.repository import RecordRepository

from .upload_agent import run_znzmo_upload

logger = logging.getLogger(__name__)

UPLOAD_SITE = "znzmo"


class UploadOrchestrator:
    """知末批量上传编排器。

    Args:
        model_root: 模型根目录（如 data/models），将递归扫描子目录。
        dry_run: 是否 dry-run 模式（提交后立即撤销）。
    """

    def __init__(
        self,
        model_root: str | Path,
        dry_run: bool = False,
        scan_interval_minutes: int | None = None,
    ):
        self.model_root = Path(model_root)
        self.dry_run = dry_run
        self.config = get_config().publish
        self.scan_interval_minutes = (
            scan_interval_minutes
            if scan_interval_minutes is not None
            else getattr(self.config, "scan_interval_minutes", 60)
        )
        self.repo = RecordRepository()

    # ------------------------------------------------------------------
    # 扫描
    # ------------------------------------------------------------------

    def _scan_models(self) -> list[tuple[Path, str]]:
        """扫描所有待上传的模型目录。

        返回 (Path, resolved_str) 列表，避免在 async 上下文中调用 Path 阻塞方法。

        条件：
        - 目录下存在 meta.json
        - 目录下存在 extracted/ 子目录（已完成后处理）
        - 未在 records 中标记为 completed
        """
        models: list[tuple[Path, str]] = []
        if not self.model_root.exists():
            logger.warning(f"模型根目录不存在: {self.model_root}")
            return models

        for meta_file in self.model_root.rglob("meta.json"):
            model_dir = meta_file.parent
            model_dir_str = str(model_dir.resolve())

            # 过滤已上传成功
            if self.repo.is_completed(UPLOAD_SITE, model_dir_str):
                logger.debug(f"已上传，跳过: {model_dir.name}")
                continue

            # 必须有 extracted/ 目录
            if not (model_dir / "extracted").exists():
                logger.debug(f"无 extracted/ 目录，跳过: {model_dir.name}")
                continue

            models.append((model_dir, model_dir_str))

        # 按目录名排序，保证确定性
        models.sort(key=lambda t: t[0].name)
        return models

    # ------------------------------------------------------------------
    # 单条上传
    # ------------------------------------------------------------------

    async def _upload_single(self, model_dir: Path, model_dir_str: str) -> bool:
        """上传单个模型。返回 True 表示成功完成。"""
        logger.info(f"上传: {model_dir.name}")

        try:
            result = await run_znzmo_upload(model_dir_str, dry_run=self.dry_run)
            if result.startswith("失败"):
                logger.error(f"上传失败: {model_dir.name} — {result}")
                return False
            logger.info(f"上传成功: {model_dir.name} — {result}")
            return True
        except Exception:
            logger.exception(f"上传异常: {model_dir.name}")
            # 补充记录失败（防止 agent 内部未记录）
            self.repo.set(
                UPLOAD_SITE,
                model_dir_str,
                step=WorkflowStep.FAILED,
                status=WorkflowStatus.FAILED,
            )
            return False

    # ------------------------------------------------------------------
    # 批量模式
    # ------------------------------------------------------------------

    def run_batch(self, limit: int = 20) -> int:
        """批量模式：成功上传 limit 个模型后退出。返回成功上传数。

        只计数 **成功完成** 的任务（与 CrawlOrchestrator.run_batch 一致）。
        """
        count = 0
        models = self._scan_models()
        logger.info(f"扫描到 {len(models)} 个待上传模型，目标: {limit} 个")

        for model_dir, model_dir_str in models:
            if count >= limit:
                logger.info(f"已达到目标数量 {limit}，结束批量上传")
                break

            success = asyncio.run(self._upload_single(model_dir, model_dir_str))
            if success:
                count += 1

            # 请求间隔，避免对知末服务器造成压力
            time.sleep(2)

        logger.info(f"批量上传结束，成功: {count}/{limit}")
        return count

    # ------------------------------------------------------------------
    # 守护模式
    # ------------------------------------------------------------------

    def run_daemon(self) -> None:
        """守护模式：循环扫描模型目录并上传新模型。"""
        logger.info(
            f"守护模式启动，扫描间隔: {self.scan_interval_minutes} 分钟，"
            f"模型根目录: {self.model_root}"
        )

        while True:
            models = self._scan_models()
            if not models:
                logger.info("无待上传模型，等待下一轮扫描...")
            else:
                logger.info(f"本轮扫描到 {len(models)} 个待上传模型")
                for model_dir, model_dir_str in models:
                    asyncio.run(self._upload_single(model_dir, model_dir_str))
                    time.sleep(2)

            logger.info(f"本轮完成，等待 {self.scan_interval_minutes} 分钟后继续...")
            time.sleep(self.scan_interval_minutes * 60)
