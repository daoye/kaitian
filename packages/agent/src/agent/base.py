"""Agent 通用基础设施 — LLM 调用、响应解析、决策框架。"""

import json
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate

from .config import create_llm


@dataclass
class Decision:
    """LLM 决策结果。"""
    action: str
    reasoning: str


async def llm_decide(prompt: ChatPromptTemplate, **variables) -> Decision:
    """通用 LLM 决策：执行 prompt 并解析为 Decision。"""
    llm = create_llm(temperature=0.1)
    chain = prompt | llm
    resp = await chain.ainvoke(variables)
    content = resp.content if hasattr(resp, "content") else str(resp)
    parsed = parse_llm_json(content)
    return Decision(
        action=parsed.get("action", "放弃"),
        reasoning=parsed.get("reasoning", ""),
    )


def parse_llm_json(content: str) -> dict:
    """解析 LLM 返回的 JSON（兼容 markdown 代码块包裹）。"""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n", 1)
        if len(lines) > 1:
            content = lines[1]
        content = content.rsplit("```", 1)[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}
