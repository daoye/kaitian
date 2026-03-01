"""关键词宇宙管理服务 - 管理用户定义的关键词集合。"""

import uuid
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.db import KeywordUniverse
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeywordService:
    """关键词宇宙管理服务。"""

    @staticmethod
    def create_universe(
        db: Session,
        name: str,
        description: Optional[str],
        keywords: List[str],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> KeywordUniverse:
        """创建关键词宇宙。

        Args:
            db: 数据库会话
            name: 宇宙名称
            description: 描述
            keywords: 关键词列表
            category: 分类
            tags: 标签列表

        Returns:
            创建的 KeywordUniverse 对象
        """
        universe_id = str(uuid.uuid4())

        try:
            universe = KeywordUniverse(
                id=universe_id,
                name=name,
                description=description,
                category=category,
                tags=json.dumps(tags or []),
                keywords=json.dumps(keywords),
                is_active=True,
            )
            db.add(universe)
            db.commit()
            db.refresh(universe)
            logger.info(f"Created keyword universe: {universe_id}")
            return universe
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create keyword universe: {str(e)}")
            raise

    @staticmethod
    def get_universe(db: Session, universe_id: str) -> Optional[KeywordUniverse]:
        """获取单个关键词宇宙。

        Args:
            db: 数据库会话
            universe_id: 宇宙 ID

        Returns:
            KeywordUniverse 对象或 None
        """
        return db.query(KeywordUniverse).filter(KeywordUniverse.id == universe_id).first()

    @staticmethod
    def get_all_universes(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> tuple[List[KeywordUniverse], int]:
        """获取所有关键词宇宙。

        Args:
            db: 数据库会话
            limit: 限制数
            offset: 偏移
            active_only: 仅返回活跃的

        Returns:
            (宇宙列表, 总数)
        """
        query = db.query(KeywordUniverse)
        if active_only:
            query = query.filter(KeywordUniverse.is_active == True)

        total = query.count()
        universes = (
            query.order_by(KeywordUniverse.created_at.desc()).limit(limit).offset(offset).all()
        )
        return universes, total

    @staticmethod
    def update_universe(
        db: Session,
        universe_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[KeywordUniverse]:
        """更新关键词宇宙。

        Args:
            db: 数据库会话
            universe_id: 宇宙 ID
            name: 新名称
            description: 新描述
            keywords: 新关键词列表
            category: 新分类
            tags: 新标签列表

        Returns:
            更新后的 KeywordUniverse 对象或 None
        """
        try:
            universe = db.query(KeywordUniverse).filter(KeywordUniverse.id == universe_id).first()

            if not universe:
                logger.warning(f"Universe not found: {universe_id}")
                return None

            if name is not None:
                universe.name = name
            if description is not None:
                universe.description = description
            if keywords is not None:
                universe.keywords = json.dumps(keywords)
            if category is not None:
                universe.category = category
            if tags is not None:
                universe.tags = json.dumps(tags)

            universe.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(universe)
            logger.info(f"Updated keyword universe: {universe_id}")
            return universe
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update keyword universe {universe_id}: {str(e)}")
            raise

    @staticmethod
    def delete_universe(db: Session, universe_id: str) -> bool:
        """删除关键词宇宙（软删除）。

        Args:
            db: 数据库会话
            universe_id: 宇宙 ID

        Returns:
            是否成功
        """
        try:
            universe = db.query(KeywordUniverse).filter(KeywordUniverse.id == universe_id).first()

            if not universe:
                logger.warning(f"Universe not found: {universe_id}")
                return False

            universe.is_active = False
            universe.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Deleted keyword universe: {universe_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete keyword universe {universe_id}: {str(e)}")
            raise

    @staticmethod
    def get_keywords_from_universe(db: Session, universe_id: str) -> List[str]:
        """从宇宙中获取关键词列表。

        Args:
            db: 数据库会话
            universe_id: 宇宙 ID

        Returns:
            关键词列表
        """
        universe = db.query(KeywordUniverse).filter(KeywordUniverse.id == universe_id).first()

        if not universe:
            return []

        try:
            return json.loads(universe.keywords)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse keywords for universe {universe_id}")
            return []


# 创建全局单例实例
keyword_service = KeywordService()
