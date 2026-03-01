"""消息推送和人工审核服务 - 处理 LihuApp 推送和 Webhook 回调。"""

import uuid
import json
import requests
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.db import GeneratedReply, ReviewNotification
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class NotificationService:
    """消息推送和审核通知服务。"""

    def __init__(self):
        self.settings = get_settings()

    def push_for_review(
        self,
        db: Session,
        reply_id: str,
        post_id: str,
        original_content: str,
        generated_reply: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = 24,
    ) -> Dict[str, Any]:
        """推送消息到 LihuApp 进行审核。

        Args:
            db: 数据库会话
            reply_id: 回复 ID
            post_id: 帖子 ID
            original_content: 原始帖子内容
            generated_reply: 生成的回复
            callback_url: 审核结果回调 URL
            metadata: 附加元数据
            expires_in_hours: 消息过期时间（小时）

        Returns:
            推送结果字典
        """
        try:
            notification_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

            # 构建消息内容
            message_content = self._build_lihuo_message(
                post_id=post_id,
                original_content=original_content,
                generated_reply=generated_reply,
                metadata=metadata,
            )

            # 调用 LihuApp API 推送消息
            lihuo_message_id = self._send_to_lihuo(message_content, callback_url)

            # 保存审核通知记录
            notification = ReviewNotification(
                id=notification_id,
                reply_id=reply_id,
                lihuo_message_id=lihuo_message_id,
                status="sent",
                callback_url=callback_url,
                expires_at=expires_at,
            )
            db.add(notification)

            # 更新回复状态
            reply = db.query(GeneratedReply).filter(GeneratedReply.id == reply_id).first()
            if reply:
                reply.review_status = "pending_review"
                reply.updated_at = datetime.utcnow()

            db.commit()

            logger.info(f"Pushed notification {notification_id} to LihuApp")

            return {
                "success": True,
                "notification_id": notification_id,
                "lihuo_message_id": lihuo_message_id,
                "status": "sent",
                "expires_at": expires_at.isoformat(),
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to push notification for reply {reply_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def handle_review_callback(
        self,
        db: Session,
        notification_id: str,
        action: str,
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理 LihuApp 的审核结果回调。

        Args:
            db: 数据库会话
            notification_id: 通知 ID
            action: 审核动作 (approved, rejected)
            user_notes: 用户备注

        Returns:
            处理结果字典
        """
        try:
            notification = (
                db.query(ReviewNotification)
                .filter(ReviewNotification.id == notification_id)
                .first()
            )

            if not notification:
                logger.warning(f"Notification not found: {notification_id}")
                return {
                    "success": False,
                    "error": "通知未找到",
                }

            # 检查是否过期
            if datetime.utcnow() > notification.expires_at:
                notification.status = "expired"
                db.commit()
                return {
                    "success": False,
                    "error": "审核已过期",
                }

            # 更新通知状态
            notification.result = action
            notification.user_notes = user_notes
            notification.status = action
            notification.callback_received = True
            notification.callback_received_at = datetime.utcnow()

            # 更新相应的回复状态
            reply = notification.reply
            if action == "approved":
                reply.review_status = "approved"
                reply.user_notes = user_notes
            elif action == "rejected":
                reply.review_status = "rejected"
                reply.user_notes = user_notes

            reply.reviewed_at = datetime.utcnow()
            reply.updated_at = datetime.utcnow()

            db.commit()

            logger.info(f"Processed review callback for notification {notification_id}: {action}")

            return {
                "success": True,
                "notification_id": notification_id,
                "action": action,
                "status": "processed",
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing review callback: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_pending_reviews(
        self,
        db: Session,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list, int]:
        """获取待审核的消息列表。

        Args:
            db: 数据库会话
            limit: 限制数
            offset: 偏移

        Returns:
            (通知列表, 总数)
        """
        query = db.query(ReviewNotification).filter(ReviewNotification.status == "sent")

        total = query.count()
        notifications = (
            query.order_by(ReviewNotification.created_at.desc()).limit(limit).offset(offset).all()
        )

        return notifications, total

    @staticmethod
    def _build_lihuo_message(
        post_id: str,
        original_content: str,
        generated_reply: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建发送给 LihuApp 的消息。"""
        return {
            "message_type": "reply_approval",
            "post_id": post_id,
            "content": {
                "original_post": original_content[:500],  # 截断长文本
                "generated_reply": generated_reply,
                "metadata": metadata or {},
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _send_to_lihuo(message: Dict[str, Any], callback_url: str) -> str:
        """发送消息到 LihuApp。

        Args:
            message: 消息内容
            callback_url: 回调 URL

        Returns:
            LihuApp 消息 ID
        """
        try:
            # 这是一个演示实现
            # 实际实现中应该调用真实的 LihuApp API
            logger.info(f"Sending message to LihuApp with callback: {callback_url}")

            # 模拟生成消息 ID
            message_id = f"lihu_{uuid.uuid4().hex[:12]}"

            # TODO: 实现真实的 LihuApp API 调用
            # response = requests.post(
            #     f"{lihuo_api_url}/send-message",
            #     json={
            #         "message": message,
            #         "callback_url": callback_url,
            #     },
            #     headers={
            #         "Authorization": f"Bearer {lihuo_api_key}",
            #     },
            # )
            # return response.json().get("message_id")

            return message_id

        except Exception as e:
            logger.error(f"Failed to send message to LihuApp: {str(e)}")
            raise


class PublishService:
    """发布管理服务 - 处理回复的发布记录。"""

    def record_publish(
        self,
        db: Session,
        post_id: str,
        reply: str,
        platform: str,
        published_url: str,
        status: str = "published",
    ) -> Dict[str, Any]:
        """记录已发布的回复。

        Args:
            db: 数据库会话
            post_id: 帖子 ID
            reply: 回复内容
            platform: 发布平台
            published_url: 发布链接
            status: 发布状态

        Returns:
            记录结果字典
        """
        try:
            # 查找对应的生成回复记录
            generated_reply = (
                db.query(GeneratedReply).filter(GeneratedReply.post_id == post_id).first()
            )

            if generated_reply:
                generated_reply.status = status
                generated_reply.published_url = published_url
                generated_reply.published_at = datetime.utcnow()
                generated_reply.updated_at = datetime.utcnow()
                db.commit()

                logger.info(f"Recorded publish for post {post_id} on {platform}")

            return {
                "success": True,
                "post_id": post_id,
                "platform": platform,
                "published_url": published_url,
                "status": status,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record publish: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_publish_history(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> tuple[list, int]:
        """获取发布历史。

        Args:
            db: 数据库会话
            limit: 限制数
            offset: 偏移
            status: 筛选状态

        Returns:
            (发布记录列表, 总数)
        """
        query = db.query(GeneratedReply).filter(GeneratedReply.status != "pending")

        if status:
            query = query.filter(GeneratedReply.status == status)

        total = query.count()
        records = (
            query.order_by(GeneratedReply.published_at.desc()).limit(limit).offset(offset).all()
        )

        return records, total


# 创建全局单例实例
notification_service = NotificationService()
publish_service = PublishService()
