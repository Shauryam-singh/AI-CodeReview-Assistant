import requests
from unittest.mock import MagicMock, patch

from app.services.context.diff_parser import parse_commentable_lines
from app.services.github.review_service import (
    MAX_INLINE_COMMENTS,
    build_review_comments,
    post_pr_review,
)

DIFF = """\
diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -10,4 +10,5 @@ def handler(req):
 context_line_10
-removed_line_11
+added_line_11
+added_line_12
 context_line_13
 context_line_14
@@ -30,2 +32,2 @@ def other():
 context_line_32
-removed_line_33
+added_line_33
diff --git a/new.py b/new.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/new.py
@@ -0,0 +1,3 @@
+line_1
+line_2
+line_3
"""


def test_parse_commentable_lines_basic():
    files = parse_commentable_lines(DIFF)
    assert set(files) == {"app.py", "new.py"}

    app = files["app.py"]
    assert app["RIGHT"] == {10, 11, 12, 13, 14, 32, 33}
    assert app["LEFT"] == {10, 11, 12, 13, 30, 31}

    new = files["new.py"]
    assert new["RIGHT"] == {1, 2, 3}
    assert new["LEFT"] == set()


def test_parse_commentable_lines_empty_diff():
    assert parse_commentable_lines("") == {}
    assert parse_commentable_lines(None) == {}


def test_parse_commentable_lines_no_hunk_body():
    diff = "diff --git a/a.py b/a.py\nindex 1..2 100644\n"
    files = parse_commentable_lines(diff)
    assert files["a.py"] == {"RIGHT": set(), "LEFT": set()}


def test_build_review_comments_places_anchored_issues():
    commentable = parse_commentable_lines(DIFF)
    issues = [
        {"file": "app.py", "line": 11, "severity": "HIGH", "tool": "semgrep",
         "message": "added line issue"},
        {"file": "new.py", "line": 2, "severity": "CRITICAL", "tool": "secret-scanner",
         "message": "secret here"},
    ]
    inline, remaining = build_review_comments(issues, commentable)

    assert remaining == []
    assert [c["path"] for c in inline] == ["app.py", "new.py"]
    assert inline[0]["line"] == 11
    assert inline[0]["side"] == "RIGHT"
    assert "added line issue" in inline[0]["body"]
    assert "**HIGH**" in inline[0]["body"]
    assert inline[1]["line"] == 2


def test_build_review_comments_keeps_unanchored_issues_out_of_diff():
    commentable = parse_commentable_lines(DIFF)
    issues = [
        {"file": "app.py", "line": 999, "message": "not in diff"},
        {"file": "untouched.py", "line": 5, "message": "file not in diff"},
        {"file": "app.py", "line": "abc", "message": "bad line"},
    ]
    inline, remaining = build_review_comments(issues, commentable)
    assert inline == []
    assert len(remaining) == 3


def test_build_review_comments_supports_left_side_deleted_lines():
    commentable = {"a.py": {"RIGHT": {1}, "LEFT": {7}}}
    issues = [{"file": "a.py", "line": 7, "message": "deleted line"}]
    inline, remaining = build_review_comments(issues, commentable)
    assert remaining == []
    assert inline[0]["side"] == "LEFT"


def test_build_review_comments_respects_limit():
    commentable = {"a.py": {"RIGHT": set(range(1, 101)), "LEFT": set()}}
    issues = [{"file": "a.py", "line": i, "message": "m"} for i in range(1, 101)]
    inline, remaining = build_review_comments(issues, commentable, limit=10)
    assert len(inline) == 10
    assert len(remaining) == 90


def test_build_review_comments_normalizes_os_separators():
    commentable = {"dir/app.py": {"RIGHT": {3}, "LEFT": set()}}
    issues = [{"file": "dir\\app.py", "line": 3, "message": "win path"}]
    inline, remaining = build_review_comments(issues, commentable)
    assert remaining == []
    assert inline[0]["path"] == "dir/app.py"


def test_build_review_comments_overflow_when_global_limit_reached():
    commentable = {"a.py": {"RIGHT": set(range(1, 60)), "LEFT": set()}}
    issues = [{"file": "a.py", "line": i, "message": "m"} for i in range(1, 60)]
    inline, remaining = build_review_comments(issues, commentable)
    assert len(inline) == MAX_INLINE_COMMENTS
    assert len(remaining) == 9


@patch("app.services.github.review_service.requests.post")
def test_post_pr_review_payload_and_success(mock_post):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 987})
    comments = [{"path": "app.py", "line": 11, "side": "RIGHT", "body": "hi"}]

    ok, status, github_id = post_pr_review("a/b", 5, "tok", "summary", comments)

    assert ok is True
    assert status == 201
    assert github_id == 987
    url = mock_post.call_args.args[0]
    assert url == "https://api.github.com/repos/a/b/pulls/5"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["event"] == "COMMENT"
    assert payload["body"] == "summary"
    assert payload["comments"] == comments
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "token tok"


@patch("app.services.github.review_service.requests.post")
def test_post_pr_review_rejected_by_github(mock_post):
    mock_post.return_value = MagicMock(status_code=422, text="Unprocessable")
    ok, status, github_id = post_pr_review("a/b", 5, "tok", "summary", [])
    assert ok is False
    assert status == 422
    assert github_id is None


@patch("app.services.github.review_service.requests.post",
       side_effect=requests.exceptions.ConnectionError("boom"))
def test_post_pr_review_network_error(mock_post):
    ok, status, github_id = post_pr_review("a/b", 5, "tok", "summary", [])
    assert ok is False
    assert status == 0
    assert github_id is None


@patch("app.services.github.review_service.requests.post")
@patch("app.services.github.review_service.requests.get")
def test_post_pr_review_reuses_existing_marker(mock_get, mock_post):
    marker = "<!-- ai-review:job-1 -->"
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: [{"id": 555, "body": f"{marker}\nsummary"}],
    )
    ok, status, github_id = post_pr_review(
        "a/b", 5, "tok", "summary", [], marker=marker
    )
    assert (ok, status, github_id) == (True, 200, 555)
    assert mock_post.call_count == 0  # no duplicate review created


@patch("app.services.github.review_service.requests.post")
@patch("app.services.github.review_service.requests.get")
def test_post_pr_review_embeds_marker_when_new(mock_get, mock_post):
    marker = "<!-- ai-review:job-1 -->"
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 987})
    ok, status, github_id = post_pr_review(
        "a/b", 5, "tok", "summary", [], marker=marker
    )
    assert (ok, status, github_id) == (True, 201, 987)
    payload = mock_post.call_args.kwargs["json"]
    assert payload["body"] == f"{marker}\nsummary"


@patch("app.services.github.review_service.requests.post")
@patch("app.services.github.review_service.requests.get")
def test_post_pr_review_finds_marker_on_later_page(mock_get, mock_post):
    marker = "<!-- ai-review:job-1 -->"
    first_page = [{"id": i, "body": f"unrelated {i}"} for i in range(100)]
    second_page = [{"id": 556, "body": f"{marker}\nsummary"}]
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: first_page),
        MagicMock(status_code=200, json=lambda: second_page),
    ]
    ok, status, github_id = post_pr_review(
        "a/b", 5, "tok", "summary", [], marker=marker
    )
    assert (ok, status, github_id) == (True, 200, 556)
    assert mock_get.call_count == 2
    assert mock_post.call_count == 0


@patch("app.services.github.review_service.requests.post")
@patch("app.services.github.review_service.requests.get",
       side_effect=requests.exceptions.ConnectionError("no list"))
def test_post_pr_review_posts_when_marker_lookup_fails(mock_get, mock_post):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 988})
    ok, _, github_id = post_pr_review(
        "a/b", 5, "tok", "summary", [], marker="<!-- ai-review:job-1 -->"
    )
    assert ok is True
    assert github_id == 988
    assert mock_post.call_count == 1
