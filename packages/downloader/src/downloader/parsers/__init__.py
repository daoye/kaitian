"""HTML 解析器注册表。

每个站点一个解析器模块，统一通过 `parse(source, html)` 调用。
"""

from typing import Any

_PARSERS: dict[str, Any] = {}


def register(name: str, module: Any) -> None:
    """注册新站点的解析器。"""
    _PARSERS[name] = module


def parse(source: str, html: str) -> dict[str, Any]:
    """根据站点名称选择对应解析器解析 HTML。"""
    mod = _PARSERS.get(source)
    if not mod:
        raise ValueError(f"不支持的站点: {source}，可用: {list(_PARSERS)}")
    return mod.parse_detail_page(html)


# 注册内置站点
from sites.three_dbrute import parsers as _three_dbrute  # noqa: E402

register("3dbrute", _three_dbrute)
