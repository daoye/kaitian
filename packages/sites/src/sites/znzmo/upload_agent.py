"""知末上传 Agent — 只负责编排和 LLM 决策。

业务逻辑委托给：
- uploader.ZnzmoUploader  — HTTP / OSS 调用
- tools                   — 文件打包、图像修复等纯函数
- agent.base/prompts      — 通用 LLM 工具和 Prompt 模板
"""

import json
from pathlib import Path

from agent import (
    TAG_GENERATION_PROMPT,
    llm_decide,
    parse_llm_json,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from core.types import WorkflowStatus, WorkflowStep
from downloader.repository import RecordRepository

from .tools import cleanup_archives, create_temp_archives, repair_image
from .uploader import ZnzmoUploader

UPLOAD_SITE = "znzmo"

DOMAIN_OPTIONS = ["室内", "建筑", "景观", "其他"]
TYPE_OPTIONS = {
    "室内": ["整体项目", "独立空间", "组件组合", "单个物件"],
    "建筑": ["整体项目", "独立空间", "组件组合", "单个物件"],
    "景观": ["整体项目", "独立空间", "组件组合", "单个物件"],
    "其他": ["其他"],
}

ANALYZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是 3D 模型发布助手。分析模型元数据，决定上传策略并生成展示名称。

【模型名称要求】
- 作为网站标题，必须具有可读性和可搜索性
- 通常使用中文，专业术语（如品牌名、设计师名）可保留英文
- 包含：品类 + 风格/特征 + 核心元素
- 长度 10-30 个字符，不要太短或太长
- 避免生硬的直译，使用国内用户熟悉的表达方式
- 示例："现代简约水晶吊灯"、"北欧风格布艺单人沙发"、"Ball 8 球形玻璃吊灯"

【分类要求】
- 领域: 室内 / 建筑 / 景观 / 其他
- 类型: 整体项目 / 独立空间 / 组件组合 / 单个物件

只返回 JSON：
```json
{{
  "domain": "室内",
  "category": "单个物件",
  "model_name": "现代简约水晶吊灯",
  "reasoning": "简要理由"
}}
```"""),
    ("human", "分析以下模型元数据：\n\n{meta_json}"),
])

COVER_ERROR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """封面图上传失败。分析错误和图片信息，决定下一步操作。
可用操作：
- 放弃：不上传封面图，直接继续提交
- 修复：尝试修复图片（转换格式、调整尺寸等）并重试

图片信息：
{image_info}

错误信息：
{error}

返回 JSON：
```json
{{"action": "放弃" | "修复", "reasoning": "理由"}}
```"""),
    ("human", "请决定如何处理封面图：{cover_path}"),
])

FILE_ERROR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """模型文件上传后解析失败。分析错误并决定如何处理。
可用操作：
- 跳过：忽略该文件，继续上传其他文件
- 中止：停止整个上传流程

错误信息：{error}
文件名：{file_name}

返回 JSON：
```json
{{"action": "跳过" | "中止", "reasoning": "理由"}}
```"""),
    ("human", "文件：{file_name}\n错误：{error}"),
])


class UploadState(TypedDict):
    model_dir: str
    dry_run: bool
    meta: dict | None
    analysis: dict | None
    temp_archives: list[str]
    temp_archives_meta: list[dict]
    uploader: ZnzmoUploader | None
    uploaded_file_keys: list[str]
    uploaded_file_parse_infos: list[dict]
    cover_keys: list[str]
    picture_info: dict | None
    classify_info: dict | None
    dimension_recommend: list[dict] | None
    sku_id: int | None
    error: str | None
    result: str
    cover_repair_attempted: NotRequired[bool]
    skip_files: NotRequired[list[int]]


# ---------------------------------------------------------------------------
# 节点 1: 分析模型
# ---------------------------------------------------------------------------

async def analyze_model(state: UploadState) -> UploadState:
    model_dir = state["model_dir"]
    model_path = Path(model_dir)

    # 检查是否已上传过
    repo = RecordRepository()
    if repo.is_completed(UPLOAD_SITE, model_dir):
        return {**state, "error": "该模型已上传过，跳过"}

    meta_file = model_path / "meta.json"
    if not meta_file.exists():
        return {**state, "error": f"meta.json 不存在: {meta_file}"}

    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    analysis = {
        "model_name": meta.get("name", ""),
        "domain": "室内",
        "category": "单个物件",
        "classify_id": None,  # 通过 API 获取，不硬编码
        "classify_list": [],  # 通过 API 获取，不硬编码
        "style": "",
        "software_version": "",
        "renderer": "",
        "exclusive": True,
        "original_type": 0,
        "tags": [],
    }

    try:
        from agent.config import create_llm
        llm = create_llm(temperature=0.3)
        meta_preview = {
            "name": meta.get("name"),
            "category": meta.get("publication", {}).get("category"),
            "tags": meta.get("metadata", {}).get("tags", []),
            "license": meta.get("license"),
            "style": meta.get("files", [{}])[0].get("style"),
        }
        chain = ANALYZE_PROMPT | llm
        resp = await chain.ainvoke({
            "meta_json": json.dumps(meta_preview, ensure_ascii=False, indent=2),
        })
        llm_result = parse_llm_json(
            resp.content if hasattr(resp, "content") else str(resp))

        if llm_result.get("domain") in DOMAIN_OPTIONS:
            analysis["domain"] = llm_result["domain"]
        cat = llm_result.get("category", "")
        if cat in TYPE_OPTIONS.get(analysis["domain"], []):
            analysis["category"] = cat
        if llm_result.get("model_name"):
            analysis["model_name"] = llm_result["model_name"]
    except Exception:
        pass

    return {**state, "meta": meta, "analysis": analysis}


# ---------------------------------------------------------------------------
# 节点 2: 生成标签（必须填满 5 个）
# ---------------------------------------------------------------------------

async def generate_tags(state: UploadState) -> UploadState:
    if state.get("error"):
        return state

    analysis: dict = state["analysis"]
    meta: dict = state["meta"]

    # 现有标签（仅作 LLM 参考，不直接使用）
    raw_existing = meta.get("metadata", {}).get("tags", [])

    print("  生成中文标签...")
    try:
        from agent.config import create_llm
        llm = create_llm(temperature=0.3)
        chain = TAG_GENERATION_PROMPT | llm
        resp = await chain.ainvoke({
            "name": analysis.get("model_name", ""),
            "domain": analysis.get("domain", "室内"),
            "category": analysis.get("category", "单个物件"),
            "software": analysis.get("software_version", ""),
            "renderer": analysis.get("renderer", ""),
            "existing_tags": json.dumps(raw_existing, ensure_ascii=False),
        })
        content = resp.content if hasattr(resp, "content") else str(resp)
        parsed = parse_llm_json(content)
        tags = parsed.get("tags", [])
    except Exception:
        tags = []

    # 截断超长标签（知末限制单个标签 ≤8 字符）
    trimmed = [t[:8] for t in tags]
    analysis["tags"] = trimmed
    print(f"  标签: {trimmed}")
    return {**state, "analysis": analysis}


# ---------------------------------------------------------------------------
# 节点 3: 重新打包
# ---------------------------------------------------------------------------

def repackage(state: UploadState) -> UploadState:
    if state.get("error"):
        return state
    try:
        archives, metas = create_temp_archives(state["model_dir"])
        return {**state, "temp_archives": archives, "temp_archives_meta": metas}
    except Exception as e:
        return {**state, "error": f"打包失败: {e}"}


# ---------------------------------------------------------------------------
# 节点 4: OSS 文件上传
# ---------------------------------------------------------------------------

async def upload_file_to_oss(state: UploadState) -> UploadState:
    if state.get("error"):
        return state

    archives = state.get("temp_archives", [])
    if not archives:
        return {**state, "error": "无待上传文件"}

    skip_files: set[int] = set(state.get("skip_files", []))
    uploader = state.get("uploader")
    if uploader is None:
        uploader = ZnzmoUploader()

    try:
        print("  获取 STS 凭证...")
        await uploader.get_sts()

        uploaded_keys: list[str] = []
        parse_infos: list[dict] = []

        for i, archive_path in enumerate(archives):
            if i in skip_files:
                print(f"  [yellow]文件 {i+1} 已被决策跳过[/yellow]")
                continue

            fpath = Path(archive_path)
            init_name = fpath.name
            print(f"  上传文件 {i+1}/{len(archives)} 到 OSS...")

            try:
                key = uploader.upload_file_to_oss(archive_path)
            except Exception as e:
                decision = await llm_decide(
                    FILE_ERROR_PROMPT, file_name=init_name, error=f"OSS上传失败: {e}",
                )
                print(
                    f"  [cyan]文件 {i+1} 决策: {decision.action} — {decision.reasoning}[/cyan]")
                if decision.action == "跳过":
                    skip_files.add(i)
                    continue
                return {**state, "error": f"文件上传失败（用户中止）: {e}", "uploader": uploader}

            uploaded_keys.append(key)
            # 将 oss_key 记录到 temp_archives_meta 中
            temp_metas = state.get("temp_archives_meta", [])
            if i < len(temp_metas):
                temp_metas[i]["oss_key"] = key
            print(f"  [green]OSS 上传成功: {key}[/green]")

            upload_scene = 0 if i == 0 else 1
            print(f"  识别文件 {i+1}...")
            try:
                await uploader.identify_file(key, upload_scene)
            except Exception as e:
                decision = await llm_decide(
                    FILE_ERROR_PROMPT, file_name=init_name, error=f"文件识别失败: {e}",
                )
                print(
                    f"  [cyan]文件 {i+1} 决策: {decision.action} — {decision.reasoning}[/cyan]")
                if decision.action == "跳过":
                    skip_files.add(i)
                    continue
                return {**state, "error": f"文件识别失败（用户中止）: {e}", "uploader": uploader}

            print(f"  等待文件 {i+1} 解析...")
            try:
                parse_info = await uploader.wait_for_parse(key)
            except Exception as e:
                decision = await llm_decide(
                    FILE_ERROR_PROMPT, file_name=init_name, error=f"文件解析失败: {e}",
                )
                print(
                    f"  [cyan]文件 {i+1} 决策: {decision.action} — {decision.reasoning}[/cyan]")
                if decision.action == "跳过":
                    skip_files.add(i)
                    continue
                return {**state, "error": f"文件解析失败（用户中止）: {e}", "uploader": uploader}

            parse_infos.append(parse_info)
            print(
                f"  [green]文件 {i+1} 解析完成: {parse_info.get('modelMainFormat', '')} v{parse_info.get('fileVersionShow', '')}[/green]")

        if not parse_infos:
            return {**state, "error": "所有文件均被跳过，无有效文件可提交", "uploader": uploader}

        return {
            **state,
            "uploader": uploader,
            "uploaded_file_keys": uploaded_keys,
            "uploaded_file_parse_infos": parse_infos,
            "skip_files": list(skip_files),
        }
    except Exception as e:
        return {**state, "error": f"文件上传失败: {e}", "uploader": uploader}


# ---------------------------------------------------------------------------
# 节点 5: 封面上传
# ---------------------------------------------------------------------------

async def upload_cover(state: UploadState) -> UploadState:
    if state.get("error"):
        return state

    model_path = Path(state["model_dir"])
    previews = model_path / "previews"
    covers = sorted(previews.iterdir()) if previews.exists() else []
    if not covers:
        print("  [yellow]无封面图，跳过[/yellow]")
        return state

    uploader = state.get("uploader")
    if uploader is None:
        uploader = ZnzmoUploader()

    # 上传所有预览图（最多10张）
    max_covers = 10
    cover_keys: list[str] = []
    for idx, cover_file in enumerate(covers[:max_covers]):
        cover_path = str(cover_file.resolve())
        print(
            f"  上传封面图 {idx+1}/{min(len(covers), max_covers)}: {cover_file.name}")

        try:
            key = await uploader.upload_cover(cover_path)
            print(f"  [green]封面上传成功: {key}[/green]")
            cover_keys.append(key)
        except Exception as e:
            error_msg = str(e)
            print(f"  [yellow]封面图 {idx+1} 上传失败: {error_msg}[/yellow]")

            # Agent 决策：放弃 or 修复
            repaired_key = await _agent_cover_decision(
                uploader, cover_path, error_msg,
            )
            if repaired_key:
                print(f"  [green]封面图 {idx+1} 修复后上传成功: {repaired_key}[/green]")
                cover_keys.append(repaired_key)
            else:
                print(f"  [yellow]封面图 {idx+1} 已放弃[/yellow]")

    if not cover_keys:
        print("  [red]所有封面图均失败，无合格封面[/red]")
        return {**state, "error": "所有封面图均无法通过验证，放弃上传", "uploader": uploader}
    else:
        print(f"  [green]共上传 {len(cover_keys)} 张封面图[/green]")
    return {**state, "cover_keys": cover_keys, "uploader": uploader}


async def _agent_cover_decision(
    uploader: ZnzmoUploader, cover_path: str, error: str,
) -> str | None:
    """Agent 决策：封面失败时选择放弃或修复。返回修复后的 key 或 None。"""
    img_info = f"路径: {cover_path}, 大小: {Path(cover_path).stat().st_size} bytes"
    try:
        from PIL import Image
        img = Image.open(cover_path)
        img_info += f", 尺寸: {img.size}, 格式: {img.format}, 模式: {img.mode}"
    except Exception:
        pass

    decision = await llm_decide(
        COVER_ERROR_PROMPT,
        image_info=img_info,
        error=error,
        cover_path=cover_path,
    )
    print(f"  [cyan]封面图决策: {decision.action} — {decision.reasoning}[/cyan]")

    if decision.action == "修复":
        try:
            repaired = repair_image(cover_path)
            key = await uploader.upload_cover(repaired)
            Path(repaired).unlink(missing_ok=True)
            return key
        except Exception as e:
            print(f"  [yellow]修复后仍失败: {e}，放弃封面图[/yellow]")
            return None

    return None


# ---------------------------------------------------------------------------
# 节点 5b: 封面图识别 & 获取分类信息
# ---------------------------------------------------------------------------

async def identify_picture(state: UploadState) -> UploadState:
    if state.get("error"):
        return state

    cover_keys = state.get("cover_keys", [])
    if not cover_keys:
        return state

    uploader = state.get("uploader")
    if uploader is None:
        uploader = ZnzmoUploader()

    try:
        print("  识别封面图信息...")
        picture_info = await uploader.picture_identify(cover_keys)
        print(f"  [dim]pictureIdentify: {picture_info}[/dim]")

        classify_name = picture_info.get("classifyName", "")
        if classify_name:
            print(f"  获取分类信息: {classify_name}")
            classify_info = await uploader.get_classify_name(classify_name)
            print(f"  [dim]分类: {classify_info.get('path', [])}[/dim]")

            field = picture_info.get("field", 0)
            kind_level = picture_info.get("kindLevel", 4)
            print("  获取维度推荐...")
            dimension_recommend = await uploader.get_dimension_recommend(
                classify_name, field, kind_level
            )

            return {
                **state,
                "picture_info": picture_info,
                "classify_info": classify_info,
                "dimension_recommend": dimension_recommend,
                "uploader": uploader,
            }
        else:
            return {**state, "picture_info": picture_info, "uploader": uploader}
    except Exception as e:
        print(f"  [yellow]封面识别失败，使用默认值: {e}[/yellow]")
        return {**state, "uploader": uploader}


# ---------------------------------------------------------------------------
# 节点 6: 提交表单
# ---------------------------------------------------------------------------

async def submit_form(state: UploadState) -> UploadState:
    if state.get("error"):
        # 失败也记录
        repo = RecordRepository()
        repo.set(UPLOAD_SITE, state["model_dir"],
                 step=WorkflowStep.FAILED, status=WorkflowStatus.FAILED)
        return state

    meta: dict = state["meta"]
    analysis: dict = state["analysis"]
    file_parse_infos = state.get("uploaded_file_parse_infos", [])
    if not file_parse_infos:
        repo = RecordRepository()
        repo.set(UPLOAD_SITE, state["model_dir"],
                 step=WorkflowStep.FAILED, status=WorkflowStatus.FAILED)
        return {**state, "error": "无已上传并解析的文件"}
    cover_keys: list[str] = state.get("cover_keys", [])
    primary_cover = cover_keys[0] if cover_keys else ""

    uploader = state.get("uploader")
    if uploader is None:
        uploader = ZnzmoUploader()

    repo = RecordRepository()
    model_dir = state["model_dir"]

    try:
        # 使用 API 返回的分类信息（优先）
        classify_info = state.get("classify_info", {})
        picture_info = state.get("picture_info", {})

        if classify_info:
            classify_id = classify_info.get("classifyid")
            classify_list = classify_info.get("path", [])
        else:
            classify_id = analysis.get("classify_id")
            classify_list = analysis.get("classify_list", [])

        if not classify_id:
            err_msg = "无法获取分类 ID，上传失败"
            print(f"  [red]{err_msg}[/red]")
            repo.set(UPLOAD_SITE, model_dir, step=WorkflowStep.FAILED, status=WorkflowStatus.FAILED)
            return {**state, "error": err_msg, "uploader": uploader}

        # 使用 pictureIdentify 返回的风格
        style = picture_info.get("style", analysis.get("style", ""))

        name = analysis.get("model_name", meta.get("name", ""))
        tags = analysis.get("tags", [])

        max_price = await uploader.get_max_price(classify_id)
        print(f"  最高定价: {max_price}知币")

        payload = {
            "classifyId": classify_id,
            "priceUnit": 1,
            "price": max_price,
            "commodityMemberLevel": 3,
            "type": 0,
            "version": file_parse_infos[0].get("modelMainFormat", "MAX"),
            "fileLength": file_parse_infos[0].get("fileLength", "0"),
            "renderer": file_parse_infos[0].get("rendererShow", "无"),
            "modelFileList": json.dumps([
                {
                    "file_name": pi["packagePath"],
                    "file_length": pi.get("fileLength", "0"),
                    "file_version": pi.get("fileVersionShow", ""),
                    "initName": state.get("temp_archives_meta", [])[i].get("initName", pi["packagePath"]) if i < len(state.get("temp_archives_meta", [])) else pi["packagePath"],
                    "coverImg": primary_cover,
                    "softName": pi.get("softName", "3Ds MAX"),
                    "renderer": pi.get("rendererShow", "无"),
                    "modelMainFormat": pi.get("modelMainFormat", "MAX"),
                    "precision": None,
                    "packageParseResultId": pi["id"],
                }
                for i, pi in enumerate(file_parse_infos)
            ]),
            "classifyList": json.dumps(classify_list, ensure_ascii=False),
            "sgtImg": json.dumps(cover_keys),
            "exclusiveType": 0,
            "labelList": json.dumps(tags, ensure_ascii=False),
            "field": 0,
            "kindLevel": 4,
            "style": style,
            "originalType": 0,
            "tagName": "",
            "fileUrl": file_parse_infos[0]["packagePath"],
            "name": name,
            "title": name,
        }

        print("  提交表单到知末...")
        result = await uploader.submit_model(payload)
        print(f"  [dim]提交响应: {result}[/dim]")

        if result.get("ret") == "0":
            raw_data = result.get("data")
            if raw_data is None or raw_data == "" or raw_data == 0:
                err_msg = f"服务器返回 ret=0 但 data 为空({raw_data!r})"
                print(f"  [red]{err_msg}[/red]")
                repo.set(UPLOAD_SITE, model_dir,
                         step=WorkflowStep.FAILED, status=WorkflowStatus.FAILED)
                return {**state, "error": err_msg, "uploader": uploader}
            sku_id = int(raw_data)
            print(f"  [green]提交成功! skuId={sku_id}[/green]")
            repo.set(UPLOAD_SITE, model_dir, step=WorkflowStep.COMPLETED,
                     status=WorkflowStatus.COMPLETED)
            return {**state, "result": f"提交成功 skuId={sku_id}", "sku_id": sku_id, "uploader": uploader}
        else:
            err_msg = result.get("msg", str(result))
            print(f"  [red]提交失败: {err_msg}[/red]")
            repo.set(UPLOAD_SITE, model_dir, step=WorkflowStep.FAILED,
                     status=WorkflowStatus.FAILED)
            return {**state, "error": f"提交失败: {err_msg}", "uploader": uploader}

    except Exception as e:
        repo.set(UPLOAD_SITE, model_dir, step=WorkflowStep.FAILED,
                 status=WorkflowStatus.FAILED)
        return {**state, "error": f"提交异常: {e}", "uploader": uploader}


# ---------------------------------------------------------------------------
# 节点 7: 清理
# ---------------------------------------------------------------------------

def cleanup(state: UploadState) -> UploadState:
    cleanup_archives(state.get("temp_archives", []))
    return state


# ---------------------------------------------------------------------------
# 节点 8: 撤销审核
# ---------------------------------------------------------------------------

async def recall_upload(state: UploadState) -> UploadState:
    sku_id = state.get("sku_id")
    if not sku_id:
        return {**state, "error": "无 skuId，无法撤销"}
    uploader = state.get("uploader")
    if uploader is None:
        uploader = ZnzmoUploader()
    try:
        await uploader.recall(sku_id)
        print(f"  [green]撤销成功: skuId={sku_id}[/green]")
        return {**state, "result": f"已撤销 skuId={sku_id}"}
    except Exception as e:
        return {**state, "error": f"撤销失败: {e}"}


# ---------------------------------------------------------------------------
# 图构建
# ---------------------------------------------------------------------------

def _after_submit(state: UploadState) -> str:
    """提交后路由: dry_run 时走撤销，否则直接结束。"""
    return "recall_upload" if state.get("dry_run") else "cleanup"


def build_graph() -> StateGraph:
    graph = StateGraph(UploadState)
    graph.add_node("analyze_model", analyze_model)
    graph.add_node("generate_tags", generate_tags)
    graph.add_node("repackage", repackage)
    graph.add_node("upload_file_to_oss", upload_file_to_oss)
    graph.add_node("upload_cover", upload_cover)
    graph.add_node("identify_picture", identify_picture)
    graph.add_node("submit_form", submit_form)
    graph.add_node("recall_upload", recall_upload)
    graph.add_node("cleanup", cleanup)

    graph.add_edge(START, "analyze_model")
    graph.add_edge("analyze_model", "generate_tags")
    graph.add_edge("generate_tags", "repackage")
    graph.add_edge("repackage", "upload_file_to_oss")
    graph.add_edge("upload_file_to_oss", "upload_cover")
    graph.add_edge("upload_cover", "identify_picture")
    graph.add_edge("identify_picture", "submit_form")
    graph.add_conditional_edges("submit_form", _after_submit, [
                                "recall_upload", "cleanup"])
    graph.add_edge("recall_upload", "cleanup")
    graph.add_edge("cleanup", END)
    return graph.compile()


def build_recall_graph() -> StateGraph:
    graph = StateGraph(UploadState)
    graph.add_node("recall_upload", recall_upload)
    graph.add_node("cleanup", cleanup)
    graph.add_edge(START, "recall_upload")
    graph.add_edge("recall_upload", "cleanup")
    graph.add_edge("cleanup", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# 外部入口
# ---------------------------------------------------------------------------

async def run_znzmo_upload(model_dir: str, dry_run: bool = False) -> str:
    graph = build_graph()
    init: UploadState = {
        "model_dir": model_dir,
        "dry_run": dry_run,
        "meta": None,
        "analysis": None,
        "temp_archives": [],
        "temp_archives_meta": [],
        "uploader": None,
        "uploaded_file_keys": [],
        "uploaded_file_parse_infos": [],
        "cover_keys": [],
        "picture_info": None,
        "classify_info": None,
        "dimension_recommend": None,
        "sku_id": None,
        "error": None,
        "result": "",
    }
    final = await graph.ainvoke(init)
    if final.get("error"):
        # 如果流程中途失败且未被 submit_form 记录，则补充记录
        repo = RecordRepository()
        if not repo.is_completed(UPLOAD_SITE, model_dir):
            repo.set(UPLOAD_SITE, model_dir, step=WorkflowStep.FAILED,
                     status=WorkflowStatus.FAILED)
        return f"失败: {final['error']}"
    parts = []
    keys = final.get("uploaded_file_keys", [])
    if keys:
        parts.append(f"文件数: {len(keys)}")
    cover_keys = final.get("cover_keys", [])
    if cover_keys:
        parts.append(f"封面: {len(cover_keys)} 张已上传")
    sku_id = final.get("sku_id")
    if sku_id:
        parts.append(f"skuId={sku_id}")
    result = final.get("result", "")
    if result:
        parts.append(result)
    if dry_run:
        parts.append("dry_run: 已提交并撤销，未留下记录")
    return " | ".join(parts) if parts else "完成"


async def run_znzmo_recall(sku_id: int) -> str:
    graph = build_recall_graph()
    init: UploadState = {
        "model_dir": "",
        "dry_run": False,
        "meta": None,
        "analysis": None,
        "temp_archives": [],
        "temp_archives_meta": [],
        "uploader": None,
        "uploaded_file_keys": [],
        "uploaded_file_parse_infos": [],
        "cover_keys": [],
        "picture_info": None,
        "classify_info": None,
        "dimension_recommend": None,
        "sku_id": sku_id,
        "error": None,
        "result": "",
    }
    final = await graph.ainvoke(init)
    if final.get("error"):
        return f"撤销失败: {final['error']}"
    return final.get("result", "撤销成功")
