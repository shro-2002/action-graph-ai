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


def create_issue(title: str, body: str, labels: list[str]) -> str:
    with _client() as c:
        r = c.post(f"/repos/{repo()}/issues", json={"title": title[:250], "body": body, "labels": labels})
    if r.status_code >= 300:
        raise TrackerError(f"GitHub {r.status_code}: {r.json().get('message', r.text)[:200]}")
    return r.json()["html_url"]


def comment(issue_url: str, body: str) -> str:
    m = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_url)
    if not m:
        raise TrackerError(f"Not a GitHub issue URL: {issue_url}")
    with _client() as c:
        r = c.post(f"/repos/{m.group(1)}/issues/{m.group(2)}/comments", json={"body": body})
    if r.status_code >= 300:
        raise TrackerError(f"GitHub {r.status_code}: {r.json().get('message', r.text)[:200]}")
    return r.json()["html_url"]
