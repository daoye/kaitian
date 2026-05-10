"""文本清洗任务 — 使用 LangGraph 编排。"""

from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from ..config import create_llm

SYSTEM_PROMPT = """你是模型文件文本清洗助手。你的任务是清理模型文件中的文本内容。

规则：
1. 保留：格式说明、渲染参数、安装方法、材质说明、模型参数、使用说明
2. 保留：插件下载地址、教程链接（对使用模型有直接帮助）
3. 删除：Copyright 声明、All Rights Reserved、License 协议、Disclaimer、推广信息、下载站水印
4. 删除：所有外部链接（电商商品页、制造商官网、平台自身链接、推广链接等）
5. 删除：制造商名称、平台信息、下载来源信息

输出格式：只输出清洗后的文本内容，不要添加任何解释或说明。
"""

CLEAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "请清洗以下文本，只保留纯技术参数和使用说明：\n\n---\n{content}\n---"),
])


class CleanState(TypedDict):
    files: list[Path]
    index: int
    results: list[str]
    error: str


def scan_files(state: CleanState) -> CleanState:
    """扫描 extracted 目录下的所有 .txt 文件。"""
    extracted_dir = Path(
        state["files"][0]).parent if state["files"] else Path()
    if not extracted_dir.exists():
        return {**state, "error": f"目录不存在: {extracted_dir}"}
    txt_files = sorted(extracted_dir.rglob("*.txt"))
    return {**state, "files": txt_files, "index": 0, "results": []}


def process_file(state: CleanState) -> CleanState:
    """读取、清洗、写回单个文件。"""
    if state["index"] >= len(state["files"]):
        return state

    fpath = state["files"][state["index"]]
    try:
        original = fpath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            original = fpath.read_text(encoding="gbk")
        except UnicodeDecodeError:
            return {
                **state,
                "results": state["results"] + [f"  {fpath.name}: ⚠️ 无法解码"],
                "index": state["index"] + 1,
            }

    llm = create_llm(temperature=0)
    chain = CLEAN_PROMPT | llm
    resp = chain.invoke({"content": original})
    cleaned = resp.content.strip()

    fpath.write_text(cleaned, encoding="utf-8")
    return {
        **state,
        "results": state["results"] + [f"  {fpath.name}: ✅ 已清洗"],
        "index": state["index"] + 1,
    }


def decide(state: CleanState) -> Literal["process_file", "done"]:
    """判断是否还有未处理的文件。"""
    if state["error"]:
        return "done"
    if state["index"] < len(state["files"]):
        return "process_file"
    return "done"


def build_graph() -> StateGraph:
    """构建文本清洗工作流图。"""
    graph = StateGraph(CleanState)

    graph.add_node("scan_files", scan_files)
    graph.add_node("process_file", process_file)
    graph.add_node("done", lambda s: s)

    graph.add_edge(START, "scan_files")
    graph.add_conditional_edges("scan_files", decide)
    graph.add_conditional_edges("process_file", decide)
    graph.add_edge("done", END)

    return graph.compile()


async def run_text_clean(model_dir: str) -> str:
    """运行文本清洗任务。"""
    graph = build_graph()
    result = await graph.ainvoke({
        "files": [Path(model_dir) / "extracted"],
        "index": 0,
        "results": [],
        "error": "",
    })

    if result["error"]:
        return f"错误: {result['error']}"
    if not result["results"]:
        return "无 .txt 文件需要处理"

    return "处理完成！\n\n" + "\n".join(result["results"])
