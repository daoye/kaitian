"""discovery 类型定义."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import Resource


@dataclass
class TimeRange:
    """时间范围."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None


@dataclass
class ScheduleConfig:
    """调度配置."""

    interval_minutes: int = 30
    max_runs: Optional[int] = None


@dataclass
class DiscoveryTask:
    """发现任务配置."""

    task_id: str
    site: str
    source_type: str
    time_range: TimeRange = field(default_factory=TimeRange)
    filters: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[ScheduleConfig] = None


@dataclass
class DiscoveredResource:
    """发现的资源."""

    resource: Resource
    discovered_at: datetime
    source_url: str
    source_type: str
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
