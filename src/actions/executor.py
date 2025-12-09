from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from src.state.user_state import UserStateManager


@dataclass
class ActionResult:
    """Result of executing an action."""
    action: str
    success: bool
    message: str
    user_id: Optional[str] = None
    new_ban_count: Optional[int] = None
    new_warning_count: Optional[int] = None
    new_timeout_count: Optional[int] = None


class ActionExecutor:
    """
    Executes moderation actions and updates user state.
    Minimal implementation - no real API calls, just state updates.
    """

    def __init__(self, state_manager: UserStateManager):
        self.state = state_manager

    def execute_actions(self, actions: List[str], user_id: str, comment: str = "") -> List[ActionResult]:
        """
        Execute a list of actions for a user.
        Returns list of results for each action.
        """
        results = []
        for action in actions:
            result = self._execute_single_action(action, user_id, comment)
            results.append(result)
        return results

    def _execute_single_action(self, action: str, user_id: str, comment: str) -> ActionResult:
        """Execute a single action."""
        action_lower = action.lower().strip()

        # Ban user
        if "ban_user" in action_lower:
            new_count = self.state.increment_ban(user_id)
            return ActionResult(
                action=action,
                success=True,
                message=f"User {user_id} banned (total bans: {new_count})",
                user_id=user_id,
                new_ban_count=new_count,
            )

        # Timeout user (5m or 10m)
        if "timeout" in action_lower:
            new_count = self.state.increment_timeout(user_id)
            duration = "10m" if "10m" in action_lower else "5m"
            return ActionResult(
                action=action,
                success=True,
                message=f"User {user_id} timed out for {duration} (total timeouts: {new_count})",
                user_id=user_id,
                new_timeout_count=new_count,
            )

        # Warn user
        if "warn_user" in action_lower or "warn" in action_lower:
            new_count = self.state.increment_warning(user_id)
            return ActionResult(
                action=action,
                success=True,
                message=f"User {user_id} warned (total warnings: {new_count})",
                user_id=user_id,
                new_warning_count=new_count,
            )

        # Delete comment
        if "delete_comment" in action_lower or "delete" in action_lower:
            new_count = self.state.increment_deleted_comment(user_id)
            return ActionResult(
                action=action,
                success=True,
                message=f"Comment deleted for user {user_id} (total deleted: {new_count})",
                user_id=user_id,
            )

        # Reply to user
        if "reply" in action_lower:
            # Try to extract message from action like "reply('message')" or "reply(message)"
            message_match = re.search(r"reply\(['\"]?([^'\"]+)['\"]?\)", action_lower)
            message = message_match.group(1) if message_match else "Please follow community guidelines"
            new_count = self.state.increment_reply(user_id)
            return ActionResult(
                action=action,
                success=True,
                message=f"Replied to user {user_id}: '{message}' (total replies: {new_count})",
                user_id=user_id,
            )

        # Log incident
        if "log_incident" in action_lower:
            return ActionResult(
                action=action,
                success=True,
                message=f"Incident logged for user {user_id}",
                user_id=user_id,
            )

        # Let comment stand (no action)
        if "let_comment_stand" in action_lower or "let_stand" in action_lower:
            return ActionResult(
                action=action,
                success=True,
                message=f"No action taken for user {user_id}",
                user_id=user_id,
            )

        # Unknown action
        return ActionResult(
            action=action,
            success=False,
            message=f"Unknown action: {action}",
            user_id=user_id,
        )

