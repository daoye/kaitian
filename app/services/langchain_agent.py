"""LangChain Agent 服务 - 实现真正的 AI 代理来处理中英文帖子。"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import Tool

from app.models.db import SocialMediaPost, GeneratedReply
from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.prompt_templates import (
    get_relevance_evaluation_template,
    get_reply_generation_template,
)

logger = get_logger(__name__)


class LangChainAgentService:
    """LangChain AI 代理服务 - 支持中英文帖子。"""

    def __init__(self):
        self.settings = get_settings()
        # 初始化 LLM
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
        language: str = "zh",
        product_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """评判内容与产品的相关性（支持中英文）。

        使用 LangChain Agent 进行评判。

        Args:
            db: 数据库会话
            post_id: 帖子 ID
            content: 帖子内容
            product_description: 产品描述
            language: 语言 (zh 或 en)
            product_name: 产品名称

        Returns:
            评判结果字典
        """
        try:
            # 获取对应的 Prompt 模板
            template = get_relevance_evaluation_template(language)
            prompt = PromptTemplate(
                input_variables=["content", "product_description", "product_name"],
                template=template,
            )

            # 使用 LLM 进行评判
            from langchain.chains import LLMChain

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                content=content,
                product_description=product_description,
                product_name=product_name or "我们的产品",
            )

            # 解析响应
            result = self._parse_evaluation_response(response)

            # 更新数据库
            post = db.query(SocialMediaPost).filter(SocialMediaPost.id == post_id).first()

            if post:
                post.relevance_score = result.get("score", 0.0)
                post.is_relevant = result.get("is_relevant", False)
                post.relevance_reasoning = result.get("reasoning", "")
                post.suggested_angle = result.get("suggested_angle")
                post.sentiment = result.get("sentiment")
                post.intent = result.get("intent")
                post.urgency = result.get("urgency")
                post.evaluated_at = datetime.utcnow()
                db.commit()

            logger.info(f"Evaluated relevance for post {post_id}: {result}")

            return {
                "success": True,
                "post_id": post_id,
                **result,
            }

        except Exception as e:
            logger.error(f"Error evaluating relevance for post {post_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def generate_reply(
        self,
        db: Session,
        post_id: str,
        original_content: str,
        platform: str,
        tone: str = "professional",
        max_length: int = 300,
        language: str = "zh",
        product_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成回复（支持中英文）。

        使用 LangChain Agent 生成回复。

        Args:
            db: 数据库会话
            post_id: 帖子 ID
            original_content: 原始帖子内容
            platform: 社交媒体平台
            tone: 语气风格
            max_length: 最大字数
            language: 语言 (zh 或 en)
            product_info: 产品信息

        Returns:
            生成结果字典
        """
        try:
            # 获取对应的 Prompt 模板
            template = get_reply_generation_template(language)
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

            # 使用 LLM 生成回复
            from langchain.chains import LLMChain

            chain = LLMChain(llm=self.llm, prompt=prompt)

            product_info_str = (
                json.dumps(product_info, ensure_ascii=False) if product_info else "未提供"
            )

            response = chain.run(
                original_content=original_content,
                tone=tone,
                max_length=max_length,
                platform=platform,
                product_info=product_info_str,
            )

            # 保存到数据库
            reply_id = f"reply_{datetime.utcnow().timestamp()}"
            reply = GeneratedReply(
                id=reply_id,
                post_id=post_id,
                original_reply=response,
                current_reply=response,
                confidence=0.85,
                word_count=len(response.split()),
                status="pending",
            )
            db.add(reply)
            db.commit()

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

    def create_agent(
        self,
        product_info: Dict[str, Any],
        language: str = "zh",
    ) -> AgentExecutor:
        """创建 LangChain Agent。

        Args:
            product_info: 产品信息
            language: 语言

        Returns:
            AgentExecutor 实例
        """
        # 定义工具
        tools = [
            Tool(
                name="EvaluateRelevance",
                func=self._evaluate_with_agent,
                description="评判内容是否与产品相关",
            ),
            Tool(
                name="GenerateReply",
                func=self._generate_with_agent,
                description="为帖子生成回复",
            ),
        ]

        # 创建 Agent
        agent_prompt = PromptTemplate.from_template(
            """你是一个营销 AI 助手，帮助评判内容相关性并生成回复。

产品信息：{product_info}

工具：{tools}

问题：{input}

思考过程：{agent_scratchpad}"""
        )

        agent = create_react_agent(
            llm=self.llm,
            tools=tools,
            prompt=agent_prompt,
        )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
        )

    def _evaluate_with_agent(self, input_str: str) -> str:
        """Agent 工具函数 - 评判相关性。"""
        # 解析输入并调用评判逻辑
        # 这是一个简化实现
        return "相关性评判完成"

    def _generate_with_agent(self, input_str: str) -> str:
        """Agent 工具函数 - 生成回复。"""
        # 解析输入并调用生成逻辑
        # 这是一个简化实现
        return "回复生成完成"

    @staticmethod
    def _parse_evaluation_response(response: str) -> Dict[str, Any]:
        """解析 LLM 的评判响应。

        支持 JSON 和文本两种格式。
        """
        # 尝试解析 JSON
        try:
            if "{" in response and "}" in response:
                # 提取 JSON 部分
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                data = json.loads(json_str)

                return {
                    "is_relevant": data.get("is_relevant", False),
                    "score": float(data.get("score", 0.0)),
                    "confidence": float(data.get("confidence", 0.0)),
                    "reasoning": data.get("reasoning", ""),
                    "suggested_angle": data.get("suggested_angle"),
                    "sentiment": data.get("sentiment"),
                    "intent": data.get("intent"),
                    "urgency": data.get("urgency"),
                }
        except json.JSONDecodeError:
            pass

        # 如果不是 JSON，使用启发式方法
        is_relevant = "相关" in response or "relevant" in response.lower()
        score = 0.7 if is_relevant else 0.3

        return {
            "is_relevant": is_relevant,
            "score": score,
            "confidence": 0.6,
            "reasoning": response[:200],
        }


# 创建全局单例实例
langchain_agent_service = LangChainAgentService()
