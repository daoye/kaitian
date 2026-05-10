"""通过 BrowserOS MCP 获取 download nonce — LangGraph 工作流。"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict


class NonceState(TypedDict):
    tools: list[Any] | None
    page_id: int | None
    nonce: str | None
    error: str | None
    result: str
    site: str
    account: str


def _parse_pages(result: Any) -> list[dict]:
    """解析 list_pages 返回的页面列表。"""
    import re
    text = _extract_text_content(result)
    pages = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"\s*(\d+)\.\s+(.+?)\s+\(tab\s+\d+\)", lines[i])
        if m:
            page_id = int(m.group(1))
            title = m.group(2).strip()
            url = lines[i + 1].strip() if i + 1 < len(lines) else ""
            pages.append({"id": page_id, "title": title, "url": url})
            i += 2
        else:
            i += 1
    return pages


def _extract_text_content(result: Any) -> str:
    """从 MCP 工具返回的内容中提取纯文本值。"""
    if isinstance(result, list):
        for block in result:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text", "").strip()
                if t and t != "null":
                    return t
        return ""
    return str(result).strip() if result else ""


def _extract_page_id(result: Any) -> int | None:
    """从 MCP 工具返回的内容中提取页面 ID。"""
    import re
    if isinstance(result, list):
        for block in result:
            if isinstance(block, dict) and block.get("type") == "text":
                m = re.search(r"Page ID:\s*(\d+)", block.get("text", ""))
                if m:
                    return int(m.group(1))
    elif isinstance(result, str):
        m = re.search(r"Page ID:\s*(\d+)", result)
        if m:
            return int(m.group(1))
    return None


async def connect_mcp(state: NonceState) -> NonceState:
    """连接 BrowserOS MCP。"""
    try:
        from langchain_mcp_adapters.client import StreamableHttpConnection
        from langchain_mcp_adapters.tools import load_mcp_tools

        conn = StreamableHttpConnection(url="http://localhost:9000/mcp", transport="http")
        tools = await load_mcp_tools(None, connection=conn, tool_name_prefix=False)
        return {**state, "tools": tools}
    except Exception as e:
        return {**state, "error": f"MCP 连接失败: {e}"}


async def navigate_and_extract(state: NonceState) -> NonceState:
    """导航到网站并提取 nonce。"""
    if state.get("error"):
        return state
    tools = state.get("tools")
    if not tools:
        return {**state, "error": "MCP 未连接"}

    tool_map = {t.name: t for t in tools}
    list_p = tool_map.get("list_pages")
    navigate = tool_map.get("navigate_page")
    evaluate = tool_map.get("evaluate_script")

    if not navigate or not evaluate:
        return {**state, "error": "MCP 工具不完整"}

    try:
        # 1. 查找已有页面或打开新页面
        pages_result = await list_p.ainvoke({})
        all_pages = _parse_pages(pages_result)
        existing = [p for p in all_pages if "3dbrute.com" in p.get("url", "")]
        if existing:
            page_id = existing[0]["id"]
            nav_result = await navigate.ainvoke({"page": page_id, "url": "https://3dbrute.com/?type=free"})
        else:
            new_page = tool_map.get("new_page")
            if not new_page:
                return {**state, "error": "缺少 new_page 工具"}
            nav_result = await new_page.ainvoke({"url": "https://3dbrute.com/?type=free"})
            page_id = _extract_page_id(nav_result)
        if not page_id:
            return {**state, "error": f"无法获取页面 ID: {nav_result}"}

        # 2. 检查登录
        logged_in = await evaluate.ainvoke({
            "page": page_id,
            "expression": "document.body.classList.contains('logged-in')",
        })
        logged_val = _extract_text_content(logged_in)
        if logged_val != "true":
            return {**state, "error": "未登录"}

        # 3. 提取 nonce
        nonce_val = await evaluate.ainvoke({
            "page": page_id,
            "expression": "window.nonce_download_nonce",
        })
        nonce = _extract_text_content(nonce_val)
        if not nonce:
            return {**state, "error": "未找到 nonce"}

        return {**state, "nonce": nonce, "page_id": page_id}
    except Exception as e:
        return {**state, "error": f"执行失败: {e}"}


async def save_nonce(state: NonceState) -> NonceState:
    """保存 nonce。"""
    if state.get("error") or not state.get("nonce"):
        return state

    import asyncio
    nonce = state["nonce"]
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "kaitian", "auth", "set-meta",
        state["site"], state["account"], "download_nonce", nonce,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    return {**state, "result": f"nonce 已保存: {nonce}"}


def build_graph() -> StateGraph:
    graph = StateGraph(NonceState)
    graph.add_node("connect_mcp", connect_mcp)
    graph.add_node("navigate_and_extract", navigate_and_extract)
    graph.add_node("save_nonce", save_nonce)
    graph.add_edge(START, "connect_mcp")
    graph.add_edge("connect_mcp", "navigate_and_extract")
    graph.add_edge("navigate_and_extract", "save_nonce")
    graph.add_edge("save_nonce", END)
    return graph.compile()


async def run_get_nonce(
    site: str = "3dbrute.com",
    account: str = "daoye.more@gmail.com",
) -> str:
    graph = build_graph()
    result = await graph.ainvoke({
        "tools": None,
        "page_id": None,
        "nonce": None,
        "error": None,
        "result": "",
        "site": site,
        "account": account,
    })
    if result.get("error"):
        return f"失败: {result['error']}"
    return result.get("result", "unknown")
