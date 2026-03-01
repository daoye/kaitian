"""内容生成服务模块 - 使用 LangChain 生成营销文章。

此模块提供了使用 LangChain 和 LLM 进行内容生成的核心功能。
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.services.prompt_templates import (
    get_article_generation_template,
    get_seo_optimization_template,
    get_content_analysis_template,
    format_keywords,
    get_length_requirement,
    get_tone_description,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


class ArticleGenerationRequest(BaseModel):
    """文章生成请求模型。"""

    topic: str
    keywords: List[str]
    tone: str = "professional"  # professional, casual, technical, friendly
    length: str = "medium"  # short, medium, long
    language: str = "zh"  # zh, en
    target_audience: str = "general"
    max_tokens: Optional[int] = None


class ArticleContent(BaseModel):
    """生成的文章内容。"""

    title: str
    body: str
    summary: str
    keywords: List[str]
    word_count: int
    seo_score: Optional[float] = None


class ArticleGenerationResponse(BaseModel):
    """文章生成响应模型。"""

    success: bool
    content: Optional[ArticleContent] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None
    error_code: Optional[str] = None


class SEOOptimizationRequest(BaseModel):
    """SEO 优化请求模型。"""

    article: str
    keywords: List[str]
    language: str = "zh"
    target_audience: str = "general"


class SEOOptimizationResponse(BaseModel):
    """SEO 优化响应模型。"""

    success: bool
    seo_score: Optional[float] = None
    keyword_analysis: Optional[Dict] = None
    optimized_article: Optional[str] = None
    meta_description: Optional[str] = None
    improvements: List[str] = []
    error: Optional[str] = None


# ============================================================================
# 内容生成服务
# ============================================================================


class ContentGenerationService:
    """使用 LangChain 的内容生成服务。"""

    def __init__(self):
        """初始化服务。"""
        self.settings = get_settings()
        self.llm = self._initialize_llm()
        self.article_chain = None
        self.seo_chain = None

    def _initialize_llm(self) -> ChatOpenAI:
        """初始化 LLM。

        Returns:
            初始化的 ChatOpenAI 实例

        Raises:
            ValueError: 如果没有配置有效的 API 密钥
        """
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未设置。请在环境变量中配置 API 密钥。")

        return ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model_name=getattr(self.settings, "openai_model", "gpt-3.5-turbo"),
            temperature=getattr(self.settings, "openai_temperature", 0.7),
            max_tokens=getattr(self.settings, "content_generation_max_tokens", 2000),
        )

    async def generate_article(
        self, request: ArticleGenerationRequest
    ) -> ArticleGenerationResponse:
        """生成文章。

        Args:
            request: 文章生成请求

        Returns:
            文章生成响应
        """
        start_time = time.time()

        try:
            # 验证输入
            if not request.topic or not request.topic.strip():
                return ArticleGenerationResponse(
                    success=False, error="主题不能为空", error_code="INVALID_TOPIC"
                )

            if not request.keywords or len(request.keywords) == 0:
                return ArticleGenerationResponse(
                    success=False, error="至少需要一个关键词", error_code="INVALID_KEYWORDS"
                )

            # 格式化输入
            keywords_str = format_keywords(request.keywords)
            length_req = get_length_requirement(request.length)
            tone_desc = get_tone_description(request.tone)

            # 获取提示模板
            template = get_article_generation_template(request.language)

            # 构建链
            chain = LLMChain(llm=self.llm, prompt=template)

            # 执行链生成文章
            logger.info(f"生成文章: {request.topic}")
            generated_text = chain.run(
                topic=request.topic,
                keywords=keywords_str,
                target_audience=request.target_audience,
                tone=tone_desc,
                length_requirement=length_req,
            )

            # 解析生成的内容
            article = self._parse_generated_article(generated_text, request.keywords)

            # 计算性能指标
            generation_time = time.time() - start_time

            return ArticleGenerationResponse(
                success=True,
                content=article,
                metadata={
                    "generation_time": round(generation_time, 2),
                    "model": self.llm.model_name,
                    "tokens_estimated": len(generated_text) // 4,  # 粗略估计
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"文章生成失败: {str(e)}")
            return ArticleGenerationResponse(
                success=False,
                error=f"内容生成失败: {str(e)}",
                error_code="API_ERROR",
                metadata={
                    "generation_time": round(time.time() - start_time, 2),
                    "error_type": type(e).__name__,
                },
            )

    async def optimize_seo(self, request: SEOOptimizationRequest) -> SEOOptimizationResponse:
        """优化文章的 SEO 表现。

        Args:
            request: SEO 优化请求

        Returns:
            SEO 优化响应
        """
        start_time = time.time()

        try:
            if not request.article or not request.article.strip():
                return SEOOptimizationResponse(success=False, error="文章内容不能为空")

            if not request.keywords:
                return SEOOptimizationResponse(success=False, error="至少需要一个关键词")

            # 获取 SEO 优化提示模板
            template = get_seo_optimization_template(request.language)

            # 构建链
            chain = LLMChain(llm=self.llm, prompt=template)

            # 执行优化
            logger.info("执行 SEO 优化")
            keywords_str = format_keywords(request.keywords)
            optimization_result = chain.run(
                article=request.article,
                keywords=keywords_str,
                target_audience=request.target_audience,
            )

            # 解析优化结果
            result_data = self._parse_json_response(optimization_result)

            return SEOOptimizationResponse(
                success=True,
                seo_score=result_data.get("seo_score"),
                keyword_analysis=result_data.get("keyword_analysis"),
                optimized_article=result_data.get("optimized_article"),
                meta_description=result_data.get("meta_description"),
                improvements=result_data.get("improvement_areas", []),
            )

        except Exception as e:
            logger.error(f"SEO 优化失败: {str(e)}")
            return SEOOptimizationResponse(success=False, error=f"SEO 优化失败: {str(e)}")

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _parse_generated_article(self, content: str, keywords: List[str]) -> ArticleContent:
        """解析生成的文章内容。

        Args:
            content: 生成的文章内容（Markdown 格式）
            keywords: 目标关键词列表

        Returns:
            解析后的 ArticleContent 对象
        """
        lines = content.split("\n")

        # 提取标题（第一个 # 标题）
        title = ""
        body_lines = []
        summary = ""

        for i, line in enumerate(lines):
            if i == 0 and line.startswith("# "):
                title = line.replace("# ", "").strip()
            else:
                body_lines.append(line)

        # 生成摘要（前 100-200 字）
        body_text = "\n".join(body_lines)
        summary_text = body_text.replace("#", "").replace("\n", "").strip()
        summary = summary_text[:200] + "..." if len(summary_text) > 200 else summary_text

        # 计算字数
        word_count = len(body_text.replace(" ", "").replace("\n", ""))

        # 计算 SEO 评分（基于关键词出现频率）
        seo_score = self._calculate_seo_score(body_text, keywords)

        return ArticleContent(
            title=title or "未标题的文章",
            body=body_text,
            summary=summary,
            keywords=keywords,
            word_count=word_count,
            seo_score=seo_score,
        )

    def _calculate_seo_score(self, content: str, keywords: List[str]) -> float:
        """计算 SEO 评分。

        Args:
            content: 文章内容
            keywords: 关键词列表

        Returns:
            SEO 评分 (0-100)
        """
        if not keywords:
            return 0.0

        content_lower = content.lower()
        keyword_count = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = content_lower.count(keyword_lower)
            keyword_count += count

        # 基础评分
        base_score = min(50, keyword_count * 10)

        # 内容长度奖励
        if len(content) > 1000:
            base_score += 20
        elif len(content) > 500:
            base_score += 10

        # 关键词密度检查
        if keyword_count > 0:
            keyword_density = (keyword_count / len(content)) * 100
            if 1 < keyword_density < 5:  # 理想范围
                base_score += 20
            elif 0.5 < keyword_density <= 1 or 5 <= keyword_density < 10:
                base_score += 10

        return min(100.0, base_score)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 JSON 响应。

        Args:
            response: LLM 返回的响应文本

        Returns:
            解析后的 JSON 字典
        """
        try:
            # 尝试直接解析 JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从响应中提取 JSON 块
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 返回默认响应
            logger.warning("无法解析 JSON 响应")
            return {
                "seo_score": 50,
                "keyword_analysis": {},
                "optimized_article": response,
                "improvement_areas": [],
            }


# ============================================================================
# 单例实例
# ============================================================================

_content_generation_service: Optional[ContentGenerationService] = None


def get_content_generation_service() -> ContentGenerationService:
    """获取内容生成服务实例（单例）。

    Returns:
        ContentGenerationService 实例
    """
    global _content_generation_service
    if _content_generation_service is None:
        _content_generation_service = ContentGenerationService()
    return _content_generation_service
