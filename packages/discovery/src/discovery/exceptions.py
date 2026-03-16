"""discovery 异常定义."""

from core.exceptions import KaitianError


class DiscoveryError(KaitianError):
    """发现模块相关错误."""

    pass


class AdapterError(DiscoveryError):
    """适配器错误."""

    pass


class DeduplicationError(DiscoveryError):
    """去重错误."""

    pass


class MonitorError(DiscoveryError):
    """监控错误."""

    pass
