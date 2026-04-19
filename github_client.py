# all GitHub REST API calls

import base64
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://api.github.com"

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, github_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _get(self, path: str, params: dict = None):
        url = f"{BASE_URL}{path}"
        time.sleep(0.5)
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.error("GET %s returned %s: %s", url, response.status_code, response.text)
            return None
        return response.json()

    def get_user(self, username: str):
        return self._get(f"/users/{username}")

    def get_repos(self, username: str):
        data = self._get(f"/users/{username}/repos", params={"per_page": 100, "sort": "updated"})
        if data is None:
            return []
        return [repo for repo in data if not repo.get("fork")]

    def get_recent_commits(self, username: str, repo_name: str, days: int = 90):
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        data = self._get(
            f"/repos/{username}/{repo_name}/commits",
            params={"since": since},
        )
        if data is None:
            return []
        return data

    def get_repo_contents(self, username: str, repo_name: str):
        data = self._get(f"/repos/{username}/{repo_name}/contents")
        if data is None:
            return []
        return [item["name"] for item in data]

    def get_readme(self, username: str, repo_name: str):
        data = self._get(f"/repos/{username}/{repo_name}/readme")
        if data is None:
            return None
        try:
            return base64.b64decode(data["content"]).decode("utf-8")
        except (KeyError, ValueError) as e:
            logger.error("Failed to decode README for %s/%s: %s", username, repo_name, e)
            return None

    def get_external_issues(self, username: str, repo_name: str):
        data = self._get(f"/repos/{username}/{repo_name}/issues", params={"state": "open"})
        if data is None:
            return []
        return [issue for issue in data if issue.get("user", {}).get("login") != username]

    def get_external_prs(self, username: str, repo_name: str):
        data = self._get(f"/repos/{username}/{repo_name}/pulls", params={"state": "open"})
        if data is None:
            return []
        return [pr for pr in data if pr.get("user", {}).get("login") != username]

    def search_users_by_topics(
        self,
        topics: list,
        language: str = None,
        max_per_topic: int = 100,
    ) -> list:
        """Search repos by topic (and optional language) and return unique owner logins.

        Uses the /search/repositories endpoint.  GitHub's search API allows 30
        authenticated requests/minute, so we sleep 2 s between calls instead of
        the usual 0.5 s.
        """
        seen: set = set()
        usernames: list = []

        for topic in topics:
            q = f"topic:{topic}"
            if language:
                q += f" language:{language}"

            url = f"{BASE_URL}/search/repositories"
            time.sleep(2)  # search API rate limit is tighter
            response = self.session.get(url, params={
                "q": q,
                "sort": "updated",
                "order": "desc",
                "per_page": min(max_per_topic, 100),
            })

            if response.status_code != 200:
                logger.error(
                    "Search for topic '%s' returned %s: %s",
                    topic, response.status_code, response.text,
                )
                continue

            items = response.json().get("items", [])
            logger.info(
                "  topic:%s%s → %d repos found",
                topic,
                f" language:{language}" if language else "",
                len(items),
            )

            for item in items:
                owner = item.get("owner", {})
                if owner.get("type") != "User":
                    continue
                login = owner.get("login")
                if login and login not in seen:
                    seen.add(login)
                    usernames.append(login)

        return usernames
