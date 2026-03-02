"""Prompt templates for LangChain content generation.

This module defines all prompt templates used in the article generation chains.
"""

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

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


# ============================================================================
# 相关性评判 Prompt 模板
# ============================================================================

RELEVANCE_EVALUATION_PROMPT_ZH = """请评判以下社交媒体内容与产品的相关性。

**要评判的内容：**
{content}

**产品信息：**
产品名称：{product_name}
产品描述：{product_description}

**评判任务：**
1. 判断这个内容是否与产品相关（是/否）
2. 给出相关性评分（0-1，0表示完全不相关，1表示高度相关）
3. 给出置信度（0-1，表示你对这个判断的确定程度）
4. 提供评判理由（简明扼要，100字以内）
5. 如果相关，建议如何回复这个内容

**请以以下JSON格式输出结果：**
{{
  "is_relevant": true/false,
  "score": 0.85,
  "confidence": 0.92,
  "reasoning": "内容讨论营销工具的选择，与我们的产品高度相关",
  "suggested_angle": "突出产品的自动化功能和易用性",
  "sentiment": "neutral/positive/negative",
  "intent": "product_evaluation/question/complaint/comparison",
  "urgency": "low/medium/high"
}}
"""

RELEVANCE_EVALUATION_PROMPT_EN = """Please evaluate the relevance of the following social media content to the product.

**Content to Evaluate:**
{content}

**Product Information:**
Product Name: {product_name}
Product Description: {product_description}

**Evaluation Task:**
1. Determine if this content is relevant to the product (yes/no)
2. Provide a relevance score (0-1, where 0 is completely irrelevant and 1 is highly relevant)
3. Provide confidence level (0-1, indicating your certainty about this judgment)
4. Provide reasoning (concise, within 100 characters)
5. If relevant, suggest how to reply to this content

**Please output the result in the following JSON format:**
{{
  "is_relevant": true/false,
  "score": 0.85,
  "confidence": 0.92,
  "reasoning": "The content discusses marketing tool selection, highly relevant to our product",
  "suggested_angle": "Highlight the product's automation capabilities and ease of use",
  "sentiment": "neutral/positive/negative",
  "intent": "product_evaluation/question/complaint/comparison",
  "urgency": "low/medium/high"
}}
"""


# ============================================================================
# 回复生成 Prompt 模板
# ============================================================================

REPLY_GENERATION_PROMPT_ZH = """请根据以下社交媒体内容，生成一个适当的回复。

**原始内容：**
{original_content}

**回复要求：**
- 平台：{platform}
- 语气风格：{tone}
- 最大字数：{max_length}

**产品信息：**
{product_info}

**生成回复的指导原则：**
1. 回复应该是有帮助的、有价值的，而不仅仅是推销产品
2. 根据指定的语气风格（{tone}）调整表述方式
3. 自然地融入产品信息，避免生硬推销
4. 考虑平台的文化和用户期望（{platform}）
5. 保持回复的长度在{max_length}字以内
6. 包含适当的号召行动（CTA），如"了解更多"或"尝试免费版本"
7. 使用友好、专业的语言

**请生成一个高质量的回复：**
"""

REPLY_GENERATION_PROMPT_EN = """Please generate an appropriate reply based on the following social media content.

**Original Content:**
{original_content}

**Reply Requirements:**
- Platform: {platform}
- Tone: {tone}
- Max Length: {max_length} characters

**Product Information:**
{product_info}

**Principles for Generating Reply:**
1. The reply should be helpful and valuable, not just a sales pitch
2. Adjust the expression according to the specified tone ({tone})
3. Naturally incorporate product information, avoiding hard selling
4. Consider platform culture and user expectations ({platform})
5. Keep the reply within {max_length} characters
6. Include appropriate call-to-action (CTA), such as "Learn More" or "Try Free Version"
7. Use friendly, professional language

**Please generate a high-quality reply:**
"""


# ============================================================================
# 新的 Prompt 获取函数
# ============================================================================


def get_relevance_evaluation_template(language: str = "zh") -> str:
    """获取相关性评判的 Prompt 模板。

    Args:
        language: 语言 ("zh" 或 "en")

    Returns:
        Prompt 模板字符串
    """
    if language == "en":
        return RELEVANCE_EVALUATION_PROMPT_EN
    else:
        return RELEVANCE_EVALUATION_PROMPT_ZH


def get_reply_generation_template(language: str = "zh") -> str:
    """获取回复生成的 Prompt 模板。

    Args:
        language: 语言 ("zh" 或 "en")

    Returns:
        Prompt 模板字符串
    """
    if language == "en":
        return REPLY_GENERATION_PROMPT_EN
    else:
        return REPLY_GENERATION_PROMPT_ZH
