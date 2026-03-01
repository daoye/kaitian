"""Prompt templates for LangChain content generation.

This module defines all prompt templates used in the article generation chains.
"""

from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage

# ============================================================================
# 文章生成 Prompt 模板
# ============================================================================

ARTICLE_GENERATION_PROMPT_ZH = """你是一位专业的内容营销写手。请根据以下要求生成一篇高质量的文章：

**文章要求：**
- 主题：{topic}
- 目标关键词：{keywords}
- 目标受众：{target_audience}
- 语气风格：{tone}
- 字数要求：{length_requirement}
- 语言：中文

**具体要求：**
1. 标题必须吸引人，至少包含一个目标关键词
2. 内容结构清晰，包含：
   - 引言（30-50字）：吸引读者注意力
   - 正文（主体）：详细阐述主题，自然融入所有关键词
   - 结论（30-50字）：总结要点和行动号召
3. 段落简洁，每段100-200字
4. 使用Markdown格式
5. 采用{tone}的语气风格
6. 针对{target_audience}的需求和关注点进行优化
7. 避免生硬植入关键词，确保内容自然流畅

**输出格式：**
请按照以下Markdown格式输出文章：
```markdown
# 标题

## 引言
...

## 第一部分
...

## 第二部分
...

## 结论
...
```"""

ARTICLE_GENERATION_PROMPT_EN = """You are a professional content marketing writer. Please generate a high-quality article based on the following requirements:

**Article Requirements:**
- Topic: {topic}
- Target Keywords: {keywords}
- Target Audience: {target_audience}
- Tone: {tone}
- Word Count: {length_requirement}
- Language: English

**Specific Guidelines:**
1. Title must be compelling and include at least one target keyword
2. Clear structure with:
   - Introduction (30-50 words): Hook the reader
   - Body: Detailed content with natural keyword integration
   - Conclusion (30-50 words): Summary and call-to-action
3. Concise paragraphs (100-200 words each)
4. Use Markdown format
5. Write in {tone} tone
6. Optimize for {target_audience}'s needs and interests
7. Integrate keywords naturally without awkward placement

**Output Format:**
Please provide the article in Markdown format:
```markdown
# Title

## Introduction
...

## Section 1
...

## Section 2
...

## Conclusion
...
```"""

# ============================================================================
# SEO 优化 Prompt 模板
# ============================================================================

SEO_OPTIMIZATION_PROMPT_ZH = """请分析以下文章的SEO表现并提供优化建议：

**文章内容：**
{article}

**目标关键词：**
{keywords}

**目标受众：**
{target_audience}

**请提供以下分析：**
1. **SEO评分** (0-100)：当前文章的SEO综合评分
2. **关键词分析**：
   - 每个关键词的出现次数
   - 关键词密度
   - 优化建议
3. **标题优化**：
   - 当前标题的问题
   - 优化后的标题建议（3个选项）
4. **内容优化**：
   - 缺失的关键词使用机会
   - 段落结构建议
   - Meta描述建议
5. **优化后的文章版本**：提供改进后的完整文章

**输出格式：**
```json
{
    "seo_score": 85,
    "keyword_analysis": {
        "关键词1": {"count": 5, "density": 1.2, "suggestion": "..."},
        "关键词2": {"count": 3, "density": 0.8, "suggestion": "..."}
    },
    "title_optimization": {
        "issues": ["..."],
        "suggestions": ["...", "...", "..."]
    },
    "meta_description": "...",
    "optimized_article": "...",
    "improvement_areas": ["..."]
}
```"""

SEO_OPTIMIZATION_PROMPT_EN = """Please analyze the SEO performance of the following article and provide optimization recommendations:

**Article Content:**
{article}

**Target Keywords:**
{keywords}

**Target Audience:**
{target_audience}

**Provide the following analysis:**
1. **SEO Score** (0-100): Overall SEO rating for the article
2. **Keyword Analysis**:
   - Occurrence count for each keyword
   - Keyword density
   - Optimization suggestions
3. **Title Optimization**:
   - Current title issues
   - Optimized title suggestions (3 options)
4. **Content Optimization**:
   - Missing keyword opportunities
   - Paragraph structure suggestions
   - Meta description suggestion
5. **Optimized Article Version**: Provide improved complete article

**Output Format:**
```json
{
    "seo_score": 85,
    "keyword_analysis": {
        "keyword1": {"count": 5, "density": 1.2, "suggestion": "..."},
        "keyword2": {"count": 3, "density": 0.8, "suggestion": "..."}
    },
    "title_optimization": {
        "issues": ["..."],
        "suggestions": ["...", "...", "..."]
    },
    "meta_description": "...",
    "optimized_article": "...",
    "improvement_areas": ["..."]
}
```"""

# ============================================================================
# 内容分析 Prompt 模板
# ============================================================================

CONTENT_ANALYSIS_PROMPT_ZH = """请分析以下内容的质量和有效性：

**内容：**
{content}

**分析维度：**
1. **内容质量** (0-100)
   - 准确性
   - 相关性
   - 完整性
2. **可读性** (0-100)
   - 段落清晰度
   - 句子复杂度
   - 逻辑流畅性
3. **参与度** (0-100)
   - 吸引力
   - 互动性
   - 行动号召
4. **主要优点**：列出3个最突出的优点
5. **改进建议**：提供3个关键改进方向

**输出格式：**
```json
{
    "quality_score": 85,
    "readability_score": 82,
    "engagement_score": 88,
    "strengths": ["...", "...", "..."],
    "improvements": ["...", "...", "..."],
    "overall_assessment": "..."
}
```"""

CONTENT_ANALYSIS_PROMPT_EN = """Please analyze the quality and effectiveness of the following content:

**Content:**
{content}

**Analysis Dimensions:**
1. **Content Quality** (0-100)
   - Accuracy
   - Relevance
   - Completeness
2. **Readability** (0-100)
   - Paragraph clarity
   - Sentence complexity
   - Logical flow
3. **Engagement** (0-100)
   - Attractiveness
   - Interactivity
   - Call-to-action
4. **Key Strengths**: List 3 main strengths
5. **Improvement Suggestions**: Provide 3 key improvement areas

**Output Format:**
```json
{
    "quality_score": 85,
    "readability_score": 82,
    "engagement_score": 88,
    "strengths": ["...", "...", "..."],
    "improvements": ["...", "...", "..."],
    "overall_assessment": "..."
}
```"""

# ============================================================================
# Prompt Template 对象
# ============================================================================


def get_article_generation_template(language: str = "zh") -> PromptTemplate:
    """获取文章生成提示模板。

    Args:
        language: 语言代码，"zh" 或 "en"

    Returns:
        PromptTemplate 对象
    """
    if language == "en":
        template = ARTICLE_GENERATION_PROMPT_EN
    else:
        template = ARTICLE_GENERATION_PROMPT_ZH

    return PromptTemplate(
        input_variables=["topic", "keywords", "target_audience", "tone", "length_requirement"],
        template=template,
    )


def get_seo_optimization_template(language: str = "zh") -> PromptTemplate:
    """获取SEO优化提示模板。

    Args:
        language: 语言代码，"zh" 或 "en"

    Returns:
        PromptTemplate 对象
    """
    if language == "en":
        template = SEO_OPTIMIZATION_PROMPT_EN
    else:
        template = SEO_OPTIMIZATION_PROMPT_ZH

    return PromptTemplate(
        input_variables=["article", "keywords", "target_audience"], template=template
    )


def get_content_analysis_template(language: str = "zh") -> PromptTemplate:
    """获取内容分析提示模板。

    Args:
        language: 语言代码，"zh" 或 "en"

    Returns:
        PromptTemplate 对象
    """
    if language == "en":
        template = CONTENT_ANALYSIS_PROMPT_EN
    else:
        template = CONTENT_ANALYSIS_PROMPT_ZH

    return PromptTemplate(input_variables=["content"], template=template)


# ============================================================================
# 辅助函数
# ============================================================================


def format_keywords(keywords: list) -> str:
    """格式化关键词列表为字符串。

    Args:
        keywords: 关键词列表

    Returns:
        格式化后的关键词字符串
    """
    return "、".join(keywords) if isinstance(keywords, list) else keywords


def get_length_requirement(length: str) -> str:
    """获取字数要求描述。

    Args:
        length: 长度类型 ("short", "medium", "long")

    Returns:
        字数要求描述
    """
    length_map = {"short": "300-500字", "medium": "500-1000字", "long": "1000+字"}
    return length_map.get(length, "500-1000字")


def get_tone_description(tone: str) -> str:
    """获取语气风格描述。

    Args:
        tone: 语气类型 ("professional", "casual", "technical", "friendly")

    Returns:
        语气风格描述
    """
    tone_map = {
        "professional": "专业、正式、权威性",
        "casual": "轻松、随意、易接近",
        "technical": "技术性、专业深度",
        "friendly": "友好、亲切、易理解",
    }
    return tone_map.get(tone, "专业")
