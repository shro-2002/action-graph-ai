"""GitHub Issues integration — the task tracker."""
import os
import re
import subprocess

import httpx

API = "https://api.github.com"


class TrackerError(RuntimeError):
    pass


def _token() -> str:
    if token := os.getenv("GITHUB_TOKEN"):
        return token
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise TrackerError("No GitHub token: set GITHUB_TOKEN or run `gh auth login`.") from exc


def repo() -> str:
    return os.getenv("GITHUB_REPO", "shro-2002/action-graph-ai")


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=API, timeout=20,
        headers={"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"},
    )


def _raise_for_status(r: httpx.Response) -> None:
    if r.status_code >= 300:
        raise TrackerError(f"GitHub {r.status_code}: {r.json().get('message', r.text)[:200]}")


def _trailer(marker: str) -> str:
    """Bot-written last line of an issue body. User text never ends the body, so it cannot fake this."""
    return f"<!-- {marker} -->"


def find_issue(marker: str) -> str | None:
    """URL of a recent action-graph issue whose body carries this marker, if one exists."""
    with _client() as c:
        r = c.get(f"/repos/{repo()}/issues", params={"labels": "action-graph", "state": "all", "per_page": 100})
    _raise_for_status(r)
    trailer = _trailer(marker)
    return next((i["html_url"] for i in r.json() if (i.get("body") or "").rstrip().endswith(trailer)), None)


def create_issue(title: str, body: str, labels: list[str], marker: str = "") -> str:
    """Idempotent per marker: a retry after a timeout returns the issue GitHub already created."""
    try:
        if marker and (found := find_issue(marker)):
            return found
        with _client() as c:
            r = c.post(f"/repos/{repo()}/issues", json={"title": title[:250], "body": f"{body.replace('-->', '--&gt;')}\n\n{_trailer(marker)}", "labels": labels})
    except httpx.TimeoutException as exc:
        found = marker and find_issue(marker)
        if found:
            return found
        raise TrackerError("GitHub timed out; the item stays approved and a retry will not duplicate it.") from exc
    except httpx.HTTPError as exc:
        raise TrackerError(f"GitHub unreachable: {type(exc).__name__}") from exc
    _raise_for_status(r)
    return r.json()["html_url"]


def comment(issue_url: str, body: str) -> str:
    m = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_url)
    if not m:
        raise TrackerError(f"Not a GitHub issue URL: {issue_url}")
    try:
        with _client() as c:
            r = c.post(f"/repos/{m.group(1)}/issues/{m.group(2)}/comments", json={"body": body})
    except httpx.HTTPError as exc:
        raise TrackerError(f"GitHub unreachable: {type(exc).__name__}") from exc
    _raise_for_status(r)
    return r.json()["html_url"]
