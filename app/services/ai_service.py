"""AI 相关性评判和回复生成服务 - 使用 LangChain 和 LLM 进行 AI 处理。"""

import uuid
import json
from typing import Dict, Optional, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.models.db import SocialMediaPost, GeneratedReply
from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.prompt_templates import (
    get_relevance_evaluation_template,
    get_reply_generation_template,
)

logger = get_logger(__name__)


class RelevanceEvaluationResult:
    """相关性评判结果。"""

    def __init__(
        self,
        is_relevant: bool,
        score: float,
        confidence: float,
        reasoning: str,
        suggested_angle: Optional[str] = None,
        sentiment: Optional[str] = None,
        intent: Optional[str] = None,
        urgency: Optional[str] = None,
    ):
        self.is_relevant = is_relevant
        self.score = score
        self.confidence = confidence
        self.reasoning = reasoning
        self.suggested_angle = suggested_angle
        self.sentiment = sentiment
        self.intent = intent
        self.urgency = urgency


class AIService:
    """AI 相关性评判和回复生成服务。"""

    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
        )

    def evaluate_relevance(
        self,
        db: Session,
        post_id: str,
        content: str,
        product_description: str,
        product_name: Optional[str] = None,
    ) -> RelevanceEvaluationResult:
        """评判内容与产品的相关性。

        Args:
            db: 数据库会话
            post_id: 帖子 ID
            content: 帖子内容
            product_description: 产品描述
            product_name: 产品名称

        Returns:
            RelevanceEvaluationResult 对象
        """
        try:
            # 构建评判提示词
            template = get_relevance_evaluation_template()
            prompt = PromptTemplate(
                input_variables=["content", "product_description", "product_name"],
                template=template,
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)

            # 调用 LLM
            response = chain.run(
                content=content,
                product_description=product_description,
                product_name=product_name or "我们的产品",
            )

            # 解析响应
            result = self._parse_relevance_response(response)

            # 保存到数据库
            post = db.query(SocialMediaPost).filter(SocialMediaPost.id == post_id).first()

            if post:
                post.relevance_score = result.score
                post.is_relevant = result.is_relevant
                post.relevance_reasoning = result.reasoning
                post.suggested_angle = result.suggested_angle
                post.sentiment = result.sentiment
                post.intent = result.intent
                post.urgency = result.urgency
                post.evaluated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Evaluated relevance for post {post_id}: {result.score}")

            return result

        except Exception as e:
            logger.error(f"Error evaluating relevance for post {post_id}: {str(e)}")
            # 返回默认的不相关结果
            return RelevanceEvaluationResult(
                is_relevant=False,
                score=0.0,
                confidence=0.0,
                reasoning=f"评判失败: {str(e)}",
            )

    def generate_reply(
        self,
        db: Session,
        post_id: str,
        original_content: str,
        platform: str,
        tone: str = "professional",
        max_length: int = 300,
        product_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """为帖子生成回复。

        Args:
            db: 数据库会话
            post_id: 帖子 ID
            original_content: 原始帖子内容
            platform: 社交媒体平台
            tone: 回复语气 (professional, friendly, technical)
            max_length: 最大字数
            product_info: 产品信息

        Returns:
            包含生成回复的字典
        """
        try:
            # 构建生成提示词
            template = get_reply_generation_template()
            prompt = PromptTemplate(
                input_variables=[
                    "original_content",
                    "tone",
                    "max_length",
                    "platform",
                    "product_info",
                ],
                template=template,
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)

            product_info_str = json.dumps(product_info) if product_info else "未提供"

            # 调用 LLM
            response = chain.run(
                original_content=original_content,
                tone=tone,
                max_length=max_length,
                platform=platform,
                product_info=product_info_str,
            )

            # 保存到数据库
            reply_id = str(uuid.uuid4())
            reply = GeneratedReply(
                id=reply_id,
                post_id=post_id,
                original_reply=response,
                current_reply=response,
                confidence=0.85,  # 默认置信度
                word_count=len(response.split()),
                status="pending",
            )
            db.add(reply)
            db.commit()
            db.refresh(reply)

            logger.info(f"Generated reply for post {post_id}")

            return {
                "success": True,
                "reply_id": reply_id,
                "generated_reply": response,
                "word_count": len(response.split()),
                "confidence": 0.85,
            }

        except Exception as e:
            logger.error(f"Error generating reply for post {post_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def optimize_seo(
        self,
        content: str,
        target_keywords: List[str],
        optimization_level: str = "medium",
    ) -> Dict[str, Any]:
        """优化内容的 SEO。

        Args:
            content: 原始内容
            target_keywords: 目标关键词
            optimization_level: 优化级别 (low, medium, high)

        Returns:
            包含优化建议的字典
        """
        try:
            # TODO: 实现 SEO 优化逻辑
            logger.info(f"Optimizing SEO for content with keywords: {target_keywords}")

            return {
                "success": True,
                "original_content": content,
                "optimized_content": content,  # 实际实现中应该优化
                "seo_score": 75,
                "suggestions": [
                    "添加更多目标关键词",
                    "优化标题结构",
                    "改进段落开头",
                ],
            }

        except Exception as e:
            logger.error(f"Error optimizing SEO: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _parse_relevance_response(response: str) -> RelevanceEvaluationResult:
        """解析 LLM 的相关性评判响应。

        Args:
            response: LLM 的响应文本

        Returns:
            RelevanceEvaluationResult 对象
        """
        # 简化版的解析逻辑
        # 实际实现中应该解析 JSON 或结构化文本
        try:
            # 尝试解析 JSON 格式的响应
            data = json.loads(response)
            return RelevanceEvaluationResult(
                is_relevant=data.get("is_relevant", False),
                score=float(data.get("score", 0.0)),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                suggested_angle=data.get("suggested_angle"),
                sentiment=data.get("sentiment"),
                intent=data.get("intent"),
                urgency=data.get("urgency"),
            )
        except json.JSONDecodeError:
            # 如果不是 JSON，则基于文本内容进行启发式判断
            is_relevant = "相关" in response or "relevant" in response.lower()
            score = 0.7 if is_relevant else 0.3
            confidence = 0.6

            return RelevanceEvaluationResult(
                is_relevant=is_relevant,
                score=score,
                confidence=confidence,
                reasoning=response[:200],
            )


# 创建全局单例实例
ai_service = AIService()
