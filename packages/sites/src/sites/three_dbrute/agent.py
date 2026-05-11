"""3dbrute 智能体 — 通过 BrowserOS MCP 获取 download nonce。"""

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


def _extract_text(result: Any) -> str:
    if isinstance(result, list):
        for block in result:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text", "").strip()
                if t and t != "null":
                    return t
        return ""
    return str(result).strip() if result else ""


def _parse_pages(result: Any) -> list[dict]:
    import re
    text = _extract_text(result)
    pages = []
    for m in re.finditer(r"\s*(\d+)\.\s+(.+?)\s+\(tab\s+(\d+)\)\s*\n\s*(https?://\S+)", text):
        pages.append({"id": int(m.group(1)), "title": m.group(2).strip(), "url": m.group(4).strip()})
    if not pages:
        for m in re.finditer(r"\s*(\d+)\.\s+(.+?)\s+\(tab\s+(\d+)\)", text):
            pages.append({"id": int(m.group(1)), "title": m.group(2).strip(), "url": ""})
    return pages


def _extract_page_id(result: Any) -> int | None:
    import re
    text = _extract_text(result)
    m = re.search(r"Page ID:\s*(\d+)", text)
    return int(m.group(1)) if m else None


async def connect_mcp(state: NonceState) -> NonceState:
    try:
        from langchain_mcp_adapters.client import StreamableHttpConnection
        from langchain_mcp_adapters.tools import load_mcp_tools

        conn = StreamableHttpConnection(url="http://localhost:9000/mcp", transport="http")
        tools = await load_mcp_tools(None, connection=conn, tool_name_prefix=False)
        return {**state, "tools": tools}
    except Exception as e:
        return {**state, "error": f"MCP 连接失败: {e}"}


async def navigate_and_extract(state: NonceState) -> NonceState:
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
        pages_result = await list_p.ainvoke({})
        all_pages = _parse_pages(pages_result)
        existing = [p for p in all_pages if "3dbrute.com" in p.get("url", "")]
        if existing:
            page_id = existing[0]["id"]
            await navigate.ainvoke({"page": page_id, "url": "https://3dbrute.com/?type=free"})
        else:
            new_page = tool_map.get("new_page")
            if not new_page:
                return {**state, "error": "缺少 new_page 工具"}
            nav_result = await new_page.ainvoke({"url": "https://3dbrute.com/?type=free"})
            page_id = _extract_page_id(nav_result)
        if not page_id:
            return {**state, "error": f"无法获取页面 ID: {nav_result}"}

        import asyncio

        # 等待页面加载完成（最多 10 秒）
        await evaluate.ainvoke({
            "page": page_id,
            "expression": """
                new Promise(resolve => {
                    if (document.readyState === 'complete') resolve('ready');
                    else window.addEventListener('load', () => resolve('ready'));
                    setTimeout(() => resolve('timeout'), 10000);
                })
            """,
        })

        # 轮询等待 nonce 出现（网页可能有 AJAX 延迟加载）
        nonce = None
        for attempt in range(10):  # 最多重试 10 次
            # 检查登录状态（多种方式）
            logged_in = await evaluate.ainvoke({
                "page": page_id,
                "expression": """
                    (() => {
                        if (document.body && document.body.classList.contains('logged-in')) return 'true';
                        if (document.querySelector('.my-account, .logout, [href*="logout"]')) return 'true';
                        if (window.nonce_download_nonce) return 'true';
                        return 'false';
                    })()
                """,
            })
            logged_val = _extract_text(logged_in)

            if logged_val == "true":
                nonce_val = await evaluate.ainvoke({
                    "page": page_id,
                    "expression": "window.nonce_download_nonce",
                })
                nonce = _extract_text(nonce_val)
                if nonce:
                    break

            if attempt < 9:
                await asyncio.sleep(1)

        if logged_val != "true":
            return {**state, "error": "未登录，请先通过 BrowserOS 登录 3dbrute.com"}

        if not nonce:
            return {**state, "error": "未找到 nonce，请确保页面完全加载后再试"}

        return {**state, "nonce": nonce, "page_id": page_id}
    except Exception as e:
        return {**state, "error": f"执行失败: {e}"}


async def save_nonce(state: NonceState) -> NonceState:
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
