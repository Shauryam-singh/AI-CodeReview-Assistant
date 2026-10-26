import requests
from unittest.mock import MagicMock, patch

from app.services.github.comment_service import post_pr_comment

MARKER = "<!-- ai-review:job-1 -->"


@patch("app.services.github.comment_service.requests.post")
def test_post_pr_comment_without_marker(mock_post):
    mock_post.return_value = MagicMock(status_code=201)
    assert post_pr_comment("a/b", "5", "tok", "body") is True
    assert mock_post.call_args.kwargs["json"] == {"body": "body"}
    assert mock_post.call_count == 1


@patch("app.services.github.comment_service.requests.post")
@patch("app.services.github.comment_service.requests.get")
def test_post_pr_comment_reuses_existing_marker(mock_get, mock_post):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: [{"body": f"{MARKER}\nbody"}],
    )
    assert post_pr_comment("a/b", "5", "tok", "body", marker=MARKER) is True
    assert mock_post.call_count == 0  # no duplicate comment


@patch("app.services.github.comment_service.requests.post")
@patch("app.services.github.comment_service.requests.get")
def test_post_pr_comment_embeds_marker_when_new(mock_get, mock_post):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
    mock_post.return_value = MagicMock(status_code=201)
    assert post_pr_comment("a/b", "5", "tok", "body", marker=MARKER) is True
    assert mock_post.call_args.kwargs["json"] == {"body": f"{MARKER}\nbody"}


@patch("app.services.github.comment_service.requests.post")
@patch("app.services.github.comment_service.requests.get")
def test_post_pr_comment_finds_marker_on_later_page(mock_get, mock_post):
    first_page = [{"body": f"unrelated {i}"} for i in range(100)]
    second_page = [{"body": f"{MARKER}\nbody"}]
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: first_page),
        MagicMock(status_code=200, json=lambda: second_page),
    ]
    assert post_pr_comment("a/b", "5", "tok", "body", marker=MARKER) is True
    assert mock_get.call_count == 2
    assert mock_post.call_count == 0


@patch("app.services.github.comment_service.requests.post")
@patch("app.services.github.comment_service.requests.get",
       side_effect=requests.exceptions.ConnectionError("no list"))
def test_post_pr_comment_posts_when_marker_lookup_fails(mock_get, mock_post):
    mock_post.return_value = MagicMock(status_code=201)
    assert post_pr_comment("a/b", "5", "tok", "body", marker=MARKER) is True
    assert mock_post.call_count == 1
