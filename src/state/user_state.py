from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class UserState:
    """Tracks state for a single user."""
    user_id: str
    ban_count: int = 0
    warning_count: int = 0
    timeout_count: int = 0
    deleted_comments: int = 0
    replies_sent: int = 0
    follower_count: int = 0  # User's follower count
    viewer_count: int = 0  # Current viewer count when comment was made
    current_topic: str = ""  # Current stream topic/context
    last_action: Optional[str] = None

    def to_state_dict(self) -> Dict:
        """
        Get state representation WITHOUT user_id for memory storage.
        This is what gets stored in the memory database.
        """
        return {
            "ban_count": self.ban_count,
            "warning_count": self.warning_count,
            "timeout_count": self.timeout_count,
            "deleted_comments": self.deleted_comments,
            "replies_sent": self.replies_sent,
            "follower_count": self.follower_count,
            "viewer_count": self.viewer_count,
            "current_topic": self.current_topic,
            "last_action": self.last_action,
        }

    def to_state_string(self) -> str:
        """Convert state to a string representation for memory search."""
        state_dict = self.to_state_dict()
        parts = [
            f"bans:{state_dict['ban_count']}",
            f"warnings:{state_dict['warning_count']}",
            f"timeouts:{state_dict['timeout_count']}",
            f"deleted:{state_dict['deleted_comments']}",
            f"replies:{state_dict['replies_sent']}",
            f"followers:{state_dict['follower_count']}",
            f"viewers:{state_dict['viewer_count']}",
        ]
        if state_dict['current_topic']:
            parts.append(f"topic:{state_dict['current_topic']}")
        if state_dict['last_action']:
            parts.append(f"last_action:{state_dict['last_action']}")
        return ", ".join(parts)


class UserStateManager:
    """
    Manages user state across the moderation session.
    Tracks ban counts, warnings, timeouts, etc.
    Can persist to/load from JSON file.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        self.users: Dict[str, UserState] = {}
        self.persistence_path = persistence_path
        if persistence_path and persistence_path.exists():
            self.load(persistence_path)

    def get_user(self, user_id: str) -> UserState:
        """Get or create user state."""
        if user_id not in self.users:
            self.users[user_id] = UserState(user_id=user_id)
        return self.users[user_id]

    def increment_ban(self, user_id: str) -> int:
        """Increment ban count and return new count."""
        user = self.get_user(user_id)
        user.ban_count += 1
        user.last_action = "ban"
        return user.ban_count

    def increment_warning(self, user_id: str) -> int:
        """Increment warning count and return new count."""
        user = self.get_user(user_id)
        user.warning_count += 1
        user.last_action = "warn"
        return user.warning_count

    def increment_timeout(self, user_id: str) -> int:
        """Increment timeout count and return new count."""
        user = self.get_user(user_id)
        user.timeout_count += 1
        user.last_action = "timeout"
        return user.timeout_count

    def increment_deleted_comment(self, user_id: str) -> int:
        """Increment deleted comment count and return new count."""
        user = self.get_user(user_id)
        user.deleted_comments += 1
        user.last_action = "delete_comment"
        return user.deleted_comments

    def increment_reply(self, user_id: str) -> int:
        """Increment reply count and return new count."""
        user = self.get_user(user_id)
        user.replies_sent += 1
        user.last_action = "reply"
        return user.replies_sent

    def update_context(self, user_id: str, follower_count: int = None, viewer_count: int = None, current_topic: str = None):
        """Update contextual information for a user."""
        user = self.get_user(user_id)
        if follower_count is not None:
            user.follower_count = follower_count
        if viewer_count is not None:
            user.viewer_count = viewer_count
        if current_topic is not None:
            user.current_topic = current_topic

    def get_ban_count(self, user_id: str) -> int:
        """Get current ban count for user."""
        return self.get_user(user_id).ban_count

    def get_stats(self, user_id: str) -> Dict:
        """Get all stats for a user (includes user_id)."""
        user = self.get_user(user_id)
        return {
            "user_id": user.user_id,
            "ban_count": user.ban_count,
            "warning_count": user.warning_count,
            "timeout_count": user.timeout_count,
            "deleted_comments": user.deleted_comments,
            "replies_sent": user.replies_sent,
            "follower_count": user.follower_count,
            "viewer_count": user.viewer_count,
            "current_topic": user.current_topic,
            "last_action": user.last_action,
        }

    def get_state_dict(self, user_id: str) -> Dict:
        """Get state dict WITHOUT user_id for memory storage."""
        return self.get_user(user_id).to_state_dict()

    def get_state_string(self, user_id: str) -> str:
        """Get state string for memory search."""
        return self.get_user(user_id).to_state_string()

    def save(self, path: Optional[Path] = None) -> None:
        """Save state to JSON file."""
        save_path = path or self.persistence_path
        if not save_path:
            return
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {uid: self.get_stats(uid) for uid in self.users.keys()}
        save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        """Load state from JSON file."""
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        for uid, data in raw.items():
            self.users[uid] = UserState(
                user_id=data.get("user_id", uid),
                ban_count=data.get("ban_count", 0),
                warning_count=data.get("warning_count", 0),
                timeout_count=data.get("timeout_count", 0),
                deleted_comments=data.get("deleted_comments", 0),
                replies_sent=data.get("replies_sent", 0),
                follower_count=data.get("follower_count", 0),
                viewer_count=data.get("viewer_count", 0),
                current_topic=data.get("current_topic", ""),
                last_action=data.get("last_action"),
            )

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all users."""
        return {uid: self.get_stats(uid) for uid in self.users.keys()}
