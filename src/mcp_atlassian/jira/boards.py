"""Module for Jira boards operations."""

import logging
from typing import Any

import requests

from ..models.jira import JiraBoard
from .client import JiraClient

logger = logging.getLogger("mcp-jira")


class BoardsMixin(JiraClient):
    """Mixin for Jira boards operations."""

    def get_all_agile_boards(
        self,
        board_name: str | None = None,
        project_key: str | None = None,
        board_type: str | None = None,
        start: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get boards from Jira by name, project key, or type.

        Args:
            board_name: The name of board, support fuzzy search
            project_key: Project key (e.g., PROJECT-123)
            board_type: Board type (e.g., scrum, kanban)
            start: Start index
            limit: Maximum number of boards to return

        Returns:
            List of board information

        Raises:
            Exception: If there is an error retrieving the boards
        """
        try:
            boards = self.jira.get_all_agile_boards(
                board_name=board_name,
                project_key=project_key,
                board_type=board_type,
                start=start,
                limit=limit,
            )
            return boards.get("values", []) if isinstance(boards, dict) else []
        except requests.HTTPError as e:
            logger.error(f"Error getting all agile boards: {str(e.response.content)}")
            return []
        except Exception as e:
            logger.error(f"Error getting all agile boards: {str(e)}")
            return []

    def get_all_agile_boards_model(
        self,
        board_name: str | None = None,
        project_key: str | None = None,
        board_type: str | None = None,
        start: int = 0,
        limit: int = 50,
    ) -> list[JiraBoard]:
        """
        Get boards as JiraBoards model from Jira by name, project key, or type.

        Args:
            board_name: The name of board, support fuzzy search
            project_key: Project key (e.g., PROJECT-123)
            board_type: Board type (e.g., scrum, kanban)
            start: Start index
            limit: Maximum number of boards to return

        Returns:
            List of JiraBoards model with board information

        Raises:
            Exception: If there is an error retrieving the boards
        """
        boards = self.get_all_agile_boards(
            board_name=board_name,
            project_key=project_key,
            board_type=board_type,
            start=start,
            limit=limit,
        )
        return [JiraBoard.from_api_response(board) for board in boards]

    def move_issues_to_board(self, board_id: str, issue_keys: list[str]) -> bool:
        """Move issues from the backlog onto a board.

        Board membership is tracked separately from status, so an issue created
        via the API stays in the backlog until it is explicitly moved.

        Args:
            board_id: The board to move the issues onto.
            issue_keys: List of issue keys to move (e.g., ["PROJ-1", "PROJ-2"]).

        Returns:
            True if successful.

        Raises:
            requests.HTTPError: If the API call fails.
        """
        self.jira.post(
            f"rest/agile/1.0/board/{board_id}/issue",
            data={"issues": issue_keys},
        )
        return True

    def get_board_card_keys(self, board_id: str) -> set[str] | None:
        """Get the keys of issues actually rendered as cards on a board.

        The public Agile API cannot tell board cards from backlog items on
        team-managed boards, so this uses the internal greenhopper endpoint.

        Args:
            board_id: The board to inspect.

        Returns:
            Set of issue keys on the board, or None if the endpoint is
            unavailable (it is not part of the public API).
        """
        try:
            data = self.jira.get(
                "rest/greenhopper/1.0/xboard/work/allData",
                params={"rapidViewId": board_id},
            )
            return {issue["key"] for issue in data["issuesData"]["issues"]}
        except Exception as e:
            logger.warning(f"Could not read cards of board {board_id}: {str(e)}")
            return None
