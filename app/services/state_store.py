"""State Store Service - File-based persistence for crawler states.

This service provides file-based storage for:
- Search sessions (keywords, platforms, progress)
- Crawl checkpoints (per-page and per-batch recovery points)
- Failed items (for retry)
- Platform session data (login states, cookies, tokens)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
CHECKPOINTS_DIR = SESSIONS_DIR / "checkpoints"
FAILED_DIR = DATA_DIR / "failed"
PLATFORM_SESSIONS_DIR = FAILED_DIR / "platform_sessions"

# Ensure directories exist
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR.mkdir(parents=True, exist_ok=True)
PLATFORM_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class StateStore:
    """File-based state storage for crawler operations."""

    # ====================
    # Search Session Management
    # ====================

    @staticmethod
    def save_search_session(session_id: str, session_data: Dict[str, Any]) -> bool:
        """Save or update a search session state.

        Args:
            session_id: Unique session identifier
            session_data: Dictionary containing session state:
                - keyword: str
                - platforms: List[str]
                - status: str (pending/in_progress/completed/failed)
                - current_page: int
                - total_results: int
                - relevant_count: int
                - created_at: str (ISO format)
                - completed_at: Optional[str]
                - error_message: Optional[str]

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            session_file = SESSIONS_DIR / f"{session_id}.json"
            
            # Load existing data if any
            if session_file.exists():
                existing = StateStore._load_json(session_file)
                existing.update(session_data)
                session_data = existing
            
            session_data["updated_at"] = datetime.utcnow().isoformat()
            
            StateStore._save_json(session_file, session_data)
            logger.info(f"Search session saved: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save search session {session_id}: {str(e)}")
            return False

    @staticmethod
    def load_search_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Load a search session state.

        Args:
            session_id: Unique session identifier

        Returns:
            Session data dictionary or None if not found
        """
        try:
            session_file = SESSIONS_DIR / f"{session_id}.json"
            if not session_file.exists():
                logger.warning(f"Search session not found: {session_id}")
                return None
            
            session_data = StateStore._load_json(session_file)
            logger.info(f"Search session loaded: {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load search session {session_id}: {str(e)}")
            return None

    @staticmethod
    def list_search_sessions(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all search sessions, optionally filtered by status.

        Args:
            status_filter: Filter sessions by status (pending/in_progress/completed/failed)

        Returns:
            List of session data dictionaries
        """
        try:
            sessions = []
            for session_file in SESSIONS_DIR.glob("*.json"):
                session_data = StateStore._load_json(session_file)
                if status_filter is None or session_data.get("status") == status_filter:
                    sessions.append(session_data)
            
            # Sort by created_at descending
            sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list search sessions: {str(e)}")
            return []

    @staticmethod
    def delete_search_session(session_id: str) -> bool:
        """Delete a search session and all related data.

        Args:
            session_id: Unique session identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Delete session file
            session_file = SESSIONS_DIR / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            # Delete related checkpoints
            StateStore.cleanup_checkpoints(session_id)
            
            # Delete failed items
            failed_file = FAILED_DIR / f"{session_id}_failed.json"
            if failed_file.exists():
                failed_file.unlink()
            
            logger.info(f"Search session deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete search session {session_id}: {str(e)}")
            return False

    # ====================
    # Crawl Checkpoint Management
    # ====================

    @staticmethod
    def save_crawl_checkpoint(
        session_id: str,
        platform: str,
        page_number: int,
        cursor: Optional[str] = None,
        processed_count: int = 0,
        failed_count: int = 0,
        checkpoint_type: str = "page"  # 'page' or 'batch'
        batch_timestamp: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a crawl checkpoint for recovery.

        Args:
            session_id: Associated search session ID
            platform: Platform name (reddit, twitter, xhs, etc.)
            page_number: Current page number
            cursor: Pagination cursor for API continuation
            processed_count: Number of items processed
            failed_count: Number of items that failed
            checkpoint_type: Type of checkpoint ('page' or 'batch')
            batch_timestamp: Timestamp for batch checkpoints
            additional_data: Additional state data to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if checkpoint_type == "page":
                checkpoint_id = f"{session_id}_{platform}_page_{page_number}"
            else:
                checkpoint_id = f"{session_id}_{platform}_batch_{batch_timestamp or datetime.utcnow().timestamp()}"
            
            checkpoint_file = CHECKPOINTS_DIR / f"{checkpoint_id}.json"
            
            checkpoint_data = {
                "session_id": session_id,
                "platform": platform,
                "page_number": page_number,
                "cursor": cursor,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "type": checkpoint_type,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat(),
                "additional_data": additional_data or {},
            }
            
            StateStore._save_json(checkpoint_file, checkpoint_data)
            logger.debug(f"Checkpoint saved: {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint_id}: {str(e)}")
            return False

    @staticmethod
    def load_last_checkpoint(
        session_id: str,
        platform: Optional[str] = None,
        checkpoint_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load the last saved checkpoint for recovery.

        Args:
            session_id: Associated search session ID
            platform: Filter by platform (optional)
            checkpoint_type: Filter by type ('page' or 'batch', optional)

        Returns:
            Checkpoint data dictionary or None if not found
        """
        try:
            checkpoints = []
            
            for checkpoint_file in CHECKPOINTS_DIR.glob("*.json"):
                checkpoint_data = StateStore._load_json(checkpoint_file)
                
                # Filter by session_id
                if checkpoint_data.get("session_id") != session_id:
                    continue
                
                # Filter by platform
                if platform and checkpoint_data.get("platform") != platform:
                    continue
                
                # Filter by type
                if checkpoint_type and checkpoint_data.get("type") != checkpoint_type:
                    continue
                
                checkpoints.append((checkpoint_file, checkpoint_data))
            
            if not checkpoints:
                logger.info(f"No checkpoints found for session {session_id}")
                return None
            
            # Sort by creation time, get the latest
            checkpoints.sort(key=lambda x: x[1].get("created_at", ""), reverse=True)
            latest_checkpoint = checkpoints[0][1]
            
            logger.info(f"Last checkpoint loaded for session {session_id}: {latest_checkpoint}")
            return latest_checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint for session {session_id}: {str(e)}")
            return None

    @staticmethod
    def cleanup_checkpoints(session_id: str, keep_days: int = 7) -> int:
        """Clean up completed checkpoints for a session.

        Args:
            session_id: Associated search session ID
            keep_days: Keep checkpoints created within this many days

        Returns:
            Number of checkpoints deleted
        """
        try:
            cutoff_date = datetime.utcnow().timestamp() - (keep_days * 86400)
            deleted_count = 0
            
            for checkpoint_file in CHECKPOINTS_DIR.glob(f"{session_id}_*.json"):
                checkpoint_data = StateStore._load_json(checkpoint_file)
                created_at_str = checkpoint_data.get("created_at", "")
                
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.timestamp() < cutoff_date:
                        checkpoint_file.unlink()
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} checkpoints for session {session_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints for session {session_id}: {str(e)}")
            return 0

    # ====================
    # Failed Items Management
    # ====================

    @staticmethod
    def save_failed_item(
        session_id: str,
        item_id: str,
        item_data: Dict[str, Any],
        error_message: str,
        retry_count: int = 0
    ) -> bool:
        """Save a failed item for later retry.

        Args:
            session_id: Associated search session ID
            item_id: Unique item identifier (e.g., post URL, ID)
            item_data: Item data to retry
            error_message: Error message from failed attempt
            retry_count: Number of retry attempts made

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            failed_file = FAILED_DIR / f"{session_id}_failed.json"
            
            # Load existing failed items
            failed_items = []
            if failed_file.exists():
                failed_items = StateStore._load_json(failed_file).get("items", [])
            
            # Update or add failed item
            updated = False
            for item in failed_items:
                if item.get("item_id") == item_id:
                    item["retry_count"] = retry_count
                    item["last_failed_at"] = datetime.utcnow().isoformat()
                    item["error_message"] = error_message
                    updated = True
                    break
            
            if not updated:
                failed_items.append({
                    "item_id": item_id,
                    "item_data": item_data,
                    "error_message": error_message,
                    "retry_count": retry_count,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_failed_at": datetime.utcnow().isoformat(),
                })
            
            StateStore._save_json(failed_file, {"items": failed_items})
            logger.debug(f"Failed item saved: {item_id} (retries: {retry_count})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save failed item {item_id}: {str(e)}")
            return False

    @staticmethod
    def load_failed_items(session_id: str) -> List[Dict[str, Any]]:
        """Load all failed items for a session.

        Args:
            session_id: Associated search session ID

        Returns:
            List of failed item dictionaries
        """
        try:
            failed_file = FAILED_DIR / f"{session_id}_failed.json"
            if not failed_file.exists():
                return []
            
            failed_data = StateStore._load_json(failed_file)
            return failed_data.get("items", [])
            
        except Exception as e:
            logger.error(f"Failed to load failed items for session {session_id}: {str(e)}")
            return []

    @staticmethod
    def clear_failed_item(session_id: str, item_id: str) -> bool:
        """Remove a failed item from the list (successfully retried).

        Args:
            session_id: Associated search session ID
            item_id: Item identifier to remove

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            failed_file = FAILED_DIR / f"{session_id}_failed.json"
            if not failed_file.exists():
                return False
            
            failed_data = StateStore._load_json(failed_file)
            items = failed_data.get("items", [])
            
            # Remove the item
            items = [item for item in items if item.get("item_id") != item_id]
            
            StateStore._save_json(failed_file, {"items": items})
            logger.debug(f"Failed item cleared: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear failed item {item_id}: {str(e)}")
            return False

    # ====================
    # Platform Session Data Management
    # ====================

    @staticmethod
    def save_platform_session(
        platform: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """Save platform login/session state (cookies, tokens, etc.).

        Args:
            platform: Platform name (reddit, twitter, xhs, etc.)
            session_data: Dictionary containing session data:
                - cookies: Dict (optional)
                - tokens: Dict (optional)
                - user_agent: str (optional)
                - proxy: str (optional)
                - expires_at: Optional[str] (ISO format)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            platform_file = PLATFORM_SESSIONS_DIR / f"{platform}_session.json"
            
            session_data["updated_at"] = datetime.utcnow().isoformat()
            
            StateStore._save_json(platform_file, session_data)
            logger.info(f"Platform session saved: {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save platform session {platform}: {str(e)}")
            return False

    @staticmethod
    def load_platform_session(platform: str) -> Optional[Dict[str, Any]]:
        """Load platform login/session state.

        Args:
            platform: Platform name (reddit, twitter, xhs, etc.)

        Returns:
            Session data dictionary or None if not found
        """
        try:
            platform_file = PLATFORM_SESSIONS_DIR / f"{platform}_session.json"
            if not platform_file.exists():
                logger.info(f"Platform session not found: {platform}")
                return None
            
            session_data = StateStore._load_json(platform_file)
            
            # Check if session has expired
            expires_at = session_data.get("expires_at")
            if expires_at:
                expiry = datetime.fromisoformat(expires_at)
                if expiry < datetime.utcnow():
                    logger.warning(f"Platform session expired: {platform}")
                    return None
            
            logger.info(f"Platform session loaded: {platform}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load platform session {platform}: {str(e)}")
            return None

    @staticmethod
    def delete_platform_session(platform: str) -> bool:
        """Delete platform session data.

        Args:
            platform: Platform name (reddit, twitter, xhs, etc.)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            platform_file = PLATFORM_SESSIONS_DIR / f"{platform}_session.json"
            if platform_file.exists():
                platform_file.unlink()
                logger.info(f"Platform session deleted: {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete platform session {platform}: {str(e)}")
            return False

    # ====================
    # Utility Methods
    # ====================

    @staticmethod
    def _load_json(file_path: Path) -> Dict[str, Any]:
        """Load JSON file with error handling."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _save_json(file_path: Path, data: Dict[str, Any]):
        """Save data to JSON file with error handling."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# Singleton instance
state_store = StateStore()