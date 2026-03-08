"""Authentication and session management for platform login.

This module provides a generic login management system that can be reused
across multiple platforms (Tieba, Xiaohongshu, etc.).

Key Features:
- Cookie/session persistence
- Login state validation
- Multi-platform support
- Anti-detection measures
"""

from .login_manager import LoginManager, get_login_manager

__all__ = ["LoginManager", "get_login_manager"]
