"""Tests for the Jira BoardMixin"""

from unittest.mock import MagicMock

import pytest
import requests

from mcp_atlassian.jira import JiraConfig
from mcp_atlassian.jira.boards import BoardsMixin
from mcp_atlassian.models.jira import JiraBoard


@pytest.fixture
def mock_config():
    """Fixture to create a mock JiraConfig instance."""
    config = MagicMock(spec=JiraConfig)
    config.url = "https://test.atlassian.net"
    config.username = "test@example.com"
    config.api_token = "test-token"
    config.auth_type = "pat"
    return config


@pytest.fixture
def boards_mixin(mock_config):
    """Fixture to create a BoardsMixin instance for testing."""
    mixin = BoardsMixin(config=mock_config)
    mixin.jira = MagicMock()

    return mixin


@pytest.fixture
def mock_boards():
    """Fixture to return mock boards data."""
    return {
        "maxResults": 2,
        "startAt": 0,
        "total": 2,
        "isLast": True,
        "values": [
            {
                "id": 1000,
                "self": "https://test.atlassian.net/rest/agile/1.0/board/1000",
                "name": " Board One",
                "type": "scrum",
            },
            {
                "id": 1001,
                "self": "https://test.atlassian.net/rest/agile/1.0/board/1001",
                "name": " Board Two",
                "type": "kanban",
            },
        ],
    }


def test_get_all_agile_boards(boards_mixin, mock_boards):
    """Test get_all_agile_boards method."""
    boards_mixin.jira.get_all_agile_boards.return_value = mock_boards

    result = boards_mixin.get_all_agile_boards()
    assert result == mock_boards["values"]


def test_get_all_agile_boards_exception(boards_mixin):
    """Test get_all_agile_boards method with exception."""
    boards_mixin.jira.get_all_agile_boards.side_effect = Exception("API Error")

    result = boards_mixin.get_all_agile_boards()
    assert result == []
    boards_mixin.jira.get_all_agile_boards.assert_called_once()


def test_get_all_agile_boards_http_error(boards_mixin):
    """Test get_all_agile_boards method with HTTPError."""
    boards_mixin.jira.get_all_agile_boards.side_effect = requests.HTTPError(
        response=MagicMock(content="API Error content")
    )

    result = boards_mixin.get_all_agile_boards()
    assert result == []
    boards_mixin.jira.get_all_agile_boards.assert_called_once()


def test_get_all_agile_boards_non_dict_response(boards_mixin):
    """Test get_all_agile_boards method with non-list response."""
    boards_mixin.jira.get_all_agile_boards.return_value = "not a dict"

    result = boards_mixin.get_all_agile_boards()
    assert result == []
    boards_mixin.jira.get_all_agile_boards.assert_called_once()


def test_get_all_agile_boards_model(boards_mixin, mock_boards):
    boards_mixin.jira.get_all_agile_boards.return_value = mock_boards

    result = boards_mixin.get_all_agile_boards_model()
    assert result == [
        JiraBoard.from_api_response(value) for value in mock_boards["values"]
    ]


def test_move_issues_to_board(boards_mixin):
    """Issues are posted to the board's agile endpoint."""
    result = boards_mixin.move_issues_to_board(
        board_id="4", issue_keys=["PROJ-1", "PROJ-2"]
    )

    assert result is True
    boards_mixin.jira.post.assert_called_once_with(
        "rest/agile/1.0/board/4/issue",
        data={"issues": ["PROJ-1", "PROJ-2"]},
    )


def test_move_issues_to_board_propagates_http_error(boards_mixin):
    """A failed move must surface — silently swallowing it would report success."""
    boards_mixin.jira.post.side_effect = requests.HTTPError(
        response=MagicMock(content="API Error content")
    )

    with pytest.raises(requests.HTTPError):
        boards_mixin.move_issues_to_board(board_id="4", issue_keys=["PROJ-1"])


def test_get_board_card_keys(boards_mixin):
    """Card keys are read from the board's work data."""
    boards_mixin.jira.get.return_value = {
        "issuesData": {
            "issues": [
                {"key": "PROJ-1", "statusName": "In Progress"},
                {"key": "PROJ-2", "statusName": "Done"},
            ]
        }
    }

    result = boards_mixin.get_board_card_keys("4")

    assert result == {"PROJ-1", "PROJ-2"}
    boards_mixin.jira.get.assert_called_once_with(
        "rest/greenhopper/1.0/xboard/work/allData",
        params={"rapidViewId": "4"},
    )


def test_get_board_card_keys_unavailable(boards_mixin):
    """The endpoint is not public API — degrade to None instead of raising."""
    boards_mixin.jira.get.side_effect = Exception("404 Not Found")

    assert boards_mixin.get_board_card_keys("4") is None


def test_get_board_card_keys_unexpected_payload(boards_mixin):
    """A response without issuesData must not blow up the caller."""
    boards_mixin.jira.get.return_value = {"unexpected": "shape"}

    assert boards_mixin.get_board_card_keys("4") is None
