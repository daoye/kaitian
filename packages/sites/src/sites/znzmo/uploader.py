"""znzmo Uploader — 纯业务逻辑层，无 AI 依赖。"""

import asyncio
import secrets
import time
from pathlib import Path

import httpx
import oss2
from auth.repository import SessionRepository

API_BASE = "https://api.znzmo.com"
ZNZMO_SITE = "znzmo.com"
ZNZMO_ACCOUNT = "15908176838"
OSS_ENDPOINT = "https://oss-cn-shanghai.aliyuncs.com"
OSS_BUCKET = "znzmo-user-file"


def _get_cookies() -> dict:
    repo = SessionRepository()
    session = repo.get_by_account(ZNZMO_SITE, ZNZMO_ACCOUNT)
    if not session:
        raise RuntimeError(
            f"未找到 {ZNZMO_SITE}/{ZNZMO_ACCOUNT} 的 cookie，"
            "请先执行 kaitian auth import"
        )
    return session.cookies


class ZnzmoUploader:
    """知末上传器 — 封装所有 HTTP / OSS 调用。"""

    def __init__(self, cookies: dict | None = None):
        self.cookies = cookies or _get_cookies()
        self._sts: dict | None = None

    # ------------------------------------------------------------------
    # STS & OSS
    # ------------------------------------------------------------------

    async def get_sts(self) -> dict:
        """获取阿里云 OSS STS 临时凭证。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(f"{API_BASE}/pcenter/getUploadCredentialSTS")
            data = resp.json()
        if data.get("error", {}).get("errorCode") != "0":
            raise RuntimeError(f"STS 获取失败: {data}")
        self._sts = data["data"]
        return self._sts

    def upload_file_to_oss(self, file_path: str, key: str | None = None) -> str:
        """上传文件到 OSS，返回 OSS key。"""
        if self._sts is None:
            raise RuntimeError("STS 未获取，请先调用 get_sts()")
        auth = oss2.StsAuth(self._sts["ak"], self._sts["sk"], self._sts["token"])
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
        if key is None:
            key = f"attachment_{int(time.time() * 1000)}.zip"
        result = bucket.put_object_from_file(key, file_path)
        if result.status != 200:
            raise RuntimeError(f"OSS 上传失败: status={result.status}")
        return key

    # ------------------------------------------------------------------
    # 文件识别
    # ------------------------------------------------------------------

    async def identify_file(self, file_key: str, upload_scene: int = 0) -> None:
        """通知知末服务器文件已上传。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(
                f"{API_BASE}/personCenter/identifyUploadFile",
                params={"fileName": file_key, "type": "", "uploadScene": upload_scene},
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"文件识别失败: {data}")

    async def wait_for_parse(
        self, file_key: str, max_retries: int = 30, interval: float = 2.0,
    ) -> dict:
        """轮询 getUploadFileIdentifyInfo 直到解析完成，返回 parse result。"""
        for attempt in range(max_retries):
            async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
                resp = await client.get(
                    f"{API_BASE}/personCenter/getUploadFileIdentifyInfo",
                    params={"fileName": file_key},
                )
                data = resp.json()
            info = data.get("data", {}).get("commodityPackageParseResult", {})
            status = info.get("status")
            if status == 1:
                return info
            if status == 2:
                err = info.get("errorMsg", "解析失败")
                raise RuntimeError(f"文件解析失败: {err}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"文件解析超时: {file_key}")
            await asyncio.sleep(interval)
        return {}

    # ------------------------------------------------------------------
    # 封面上传
    # ------------------------------------------------------------------

    async def upload_cover(self, image_path: str, sts: dict | None = None) -> str:
        """上传封面图，返回 OSS key。"""
        ext = Path(image_path).suffix
        key = f"{int(time.time() * 1000)}_{secrets.token_hex(4)}{ext}"

        if sts is None:
            sts = await self.get_sts()

        auth = oss2.StsAuth(sts["ak"], sts["sk"], sts["token"])
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
        result = bucket.put_object_from_file(key, image_path)
        if result.status != 200:
            raise RuntimeError(f"封面 OSS 上传失败: status={result.status}")

        # checkPicture
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.post(
                f"{API_BASE}/personCenter/checkPicture",
                data={"file": key, "commodityType": 0},
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"封面 checkPicture 失败: {data}")

        # pictureIdentify
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.post(
                f"{API_BASE}/personCenter/pictureIdentify",
                json=[key],
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"封面 pictureIdentify 失败: {data}")

        return key

    # ------------------------------------------------------------------
    # 封面图识别 & 分类信息
    # ------------------------------------------------------------------

    async def picture_identify(self, cover_keys: list[str]) -> dict:
        """根据封面图识别风格、分类等信息。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.post(
                f"{API_BASE}/personCenter/pictureIdentify",
                params={"commodityType": 0},
                json=cover_keys,
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"pictureIdentify 失败: {data}")
        return data.get("data", {})

    async def get_classify_name(self, classify_name: str, classify_type: int = 0) -> dict:
        """获取分类路径和分类 ID。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(
                f"{API_BASE}/personCenter/getClassifyName.do",
                params={"classifyType": classify_type, "keyWord": classify_name},
            )
            data = resp.json()
        if data.get("ret") != "0":
            raise RuntimeError(f"getClassifyName 失败: {data}")
        classify_list = data.get("data", [])
        return classify_list[0] if classify_list else {}

    async def get_dimension_recommend(self, classify_name: str, field: int, kind_level: int) -> list[dict]:
        """获取分类下的维度推荐。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(
                f"{API_BASE}/personCenter/getDimensionRecommend",
                params={
                    "classifyName": classify_name,
                    "field": field,
                    "kindLevel": kind_level,
                    "commodityType": 0,
                },
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"getDimensionRecommend 失败: {data}")
        return data.get("data", [])

    # ------------------------------------------------------------------
    # 提交 / 撤销
    # ------------------------------------------------------------------

    async def get_max_price(self, classify_id: int) -> int:
        """查询分类下最高定价。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(
                f"{API_BASE}/commodityPrice/list",
                params={"createType": 0, "type": 0, "classifyId": classify_id},
            )
            data = resp.json()
        prices = []
        for item in (
            data.get("data", {}).get("obj", [])
            if isinstance(data.get("data"), dict)
            else data.get("data", [])
        ):
            p = item.get("price", 0)
            if p:
                prices.append(p)
        return max(prices) if prices else 350

    async def submit_model(self, payload: dict) -> dict:
        """提交模型表单，返回完整响应。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=60) as client:
            resp = await client.post(
                f"{API_BASE}/personCenter/uploadModelNew.do",
                data=payload,
            )
            return resp.json()

    async def recall(self, sku_id: int) -> None:
        """撤销提交审核。"""
        async with httpx.AsyncClient(cookies=self.cookies, timeout=30) as client:
            resp = await client.get(
                f"{API_BASE}/creatorCenter/recallUploadModel",
                params={"skuId": sku_id},
            )
            data = resp.json()
        code = data.get("error", {}).get("errorCode")
        if code != "0":
            raise RuntimeError(f"撤销失败: {data}")
