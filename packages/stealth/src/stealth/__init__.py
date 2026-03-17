"""stealth 模块 - 反检测/反反爬虫."""

from .__version__ import __version__
from .core import StealthManager
from .scripts import get_available_scripts, load_script, load_script_with_vars
from .types import (
    PATCH_CATALOG,
    PatchContext,
    PatchSpec,
    RiskLevel,
    FingerprintPreset,
    NoiseLevel,
    PRESET_PROFILES,
    StealthConfig,
    StealthPlan,
    StealthProfile,
    StealthSitePolicy,
    apply_site_policy,
    get_available_patches,
    get_patch_spec,
    match_host,
    resolve_enabled_patches,
    resolve_site_policy,
)

__all__ = [
    "__version__",
    "StealthManager",
    "StealthConfig",
    "StealthPlan",
    "StealthProfile",
    "StealthSitePolicy",
    "PRESET_PROFILES",
    "PATCH_CATALOG",
    "PatchSpec",
    "PatchContext",
    "RiskLevel",
    "FingerprintPreset",
    "NoiseLevel",
    "load_script",
    "load_script_with_vars",
    "get_available_scripts",
    "get_available_patches",
    "get_patch_spec",
    "resolve_enabled_patches",
    "match_host",
    "resolve_site_policy",
    "apply_site_policy",
]
