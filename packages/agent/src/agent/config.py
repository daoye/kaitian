"""LLM 配置加载器，从核心配置读取并初始化模型。"""

from core import get_config
from core.exceptions import KaitianError


class ProviderNotSupportedError(KaitianError):
    pass


_PROVIDER_MAP: dict[str, tuple[str, str]] = {}


def register_provider(name: str, module_path: str, class_name: str) -> None:
    """注册 LLM Provider。"""
    _PROVIDER_MAP[name] = (module_path, class_name)


def create_llm(**kwargs):
    """根据配置创建 LLM 实例。"""
    cfg = get_config().llm
    if cfg.provider not in _PROVIDER_MAP:
        raise ProviderNotSupportedError(
            f"不支持的 LLM provider: {cfg.provider}，可用: {list(_PROVIDER_MAP)}"
        )

    mod_path, cls_name = _PROVIDER_MAP[cfg.provider]
    import importlib
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)

    params = {"model": cfg.model, "temperature": 0.3}
    if cfg.api_key:
        params["api_key"] = cfg.api_key
    if cfg.base_url:
        params["base_url"] = cfg.base_url
    params.update(kwargs)
    return cls(**params)


# 注册内置 Provider
register_provider("deepseek", "langchain_deepseek.chat_models", "ChatDeepSeek")
