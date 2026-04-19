# Layer 2: binary flag evaluation

import base64
import re


BIO_INDIE_TERMS = {"student", "indie", "building", "founder", "solo", "independent"}


def evaluate_flags(username, user_data, repos, github_client, readme_analyzer, config) -> dict:
    return {
        "deployment_signals":      _deployment_signals(username, repos, github_client, config),
        "recent_commit_velocity":  _recent_commit_velocity(username, repos, github_client),
        "external_engagement":     _external_engagement(username, repos, github_client),
        "readme_product_voice":    _readme_product_voice(username, repos, github_client, readme_analyzer),
        "stack_sophistication":    _stack_sophistication(username, repos, github_client, config),
        "domain_focus_clustering": _domain_focus_clustering(repos),
        "complexity_progression":  _complexity_progression(username, repos, github_client),
        "bio_signals":             _bio_signals(user_data),
    }


# ---------------------------------------------------------------------------
# Individual flag evaluators
# ---------------------------------------------------------------------------

def _deployment_signals(username, repos, github_client, config) -> bool:
    indicators = set(config.DEPLOYMENT_FILE_INDICATORS)
    for repo in repos:
        contents = github_client.get_repo_contents(username, repo["name"]) or []
        if any(f in indicators for f in contents):
            return True
    return False


def _recent_commit_velocity(username, repos, github_client) -> bool:
    active_repos = 0
    for repo in repos:
        commits = github_client.get_recent_commits(username, repo["name"], days=90) or []
        if commits:
            active_repos += 1
        if active_repos >= 2:
            return True
    return False


def _external_engagement(username, repos, github_client) -> bool:
    for repo in repos:
        issues = github_client.get_external_issues(username, repo["name"]) or []
        prs = github_client.get_external_prs(username, repo["name"]) or []
        if issues or prs:
            return True
    return False


def _readme_product_voice(username, repos, github_client, readme_analyzer) -> bool:
    for repo in repos:
        readme = github_client.get_readme(username, repo["name"])
        if readme is not None:
            classification = readme_analyzer.classify_readme(readme)
            return classification == "product"
    return False


def _stack_sophistication(username, repos, github_client, config) -> bool:
    dep_files = {"package.json", "requirements.txt", "Cargo.toml"}
    categories_found = set()

    for repo in repos:
        contents = github_client.get_repo_contents(username, repo["name"]) or []
        for dep_file in dep_files:
            if dep_file not in contents:
                continue
            file_data = github_client._get(f"/repos/{username}/{repo['name']}/contents/{dep_file}")
            if not file_data or "content" not in file_data:
                continue
            try:
                text = base64.b64decode(file_data["content"]).decode("utf-8").lower()
            except (ValueError, KeyError):
                continue
            for category, packages in config.SOPHISTICATED_DEPENDENCIES.items():
                if category not in categories_found and any(pkg in text for pkg in packages):
                    categories_found.add(category)

        if len(categories_found) >= 2:
            return True

    return len(categories_found) >= 2


def _domain_focus_clustering(repos) -> bool:
    keyword_counts: dict[str, int] = {}
    for repo in repos:
        tokens = set()
        for topic in repo.get("topics") or []:
            tokens.update(_tokenize(topic))
        for word in _tokenize(repo.get("name", "")):
            tokens.add(word)
        for word in tokens:
            keyword_counts[word] = keyword_counts.get(word, 0) + 1

    return any(count >= 3 for count in keyword_counts.values())


def _complexity_progression(username, repos, github_client) -> bool:
    if len(repos) < 2:
        return False

    sorted_repos = sorted(repos, key=lambda r: r.get("created_at", ""))
    old_repos = sorted_repos[:3]
    new_repos = sorted_repos[-3:]

    # Ensure old and new sets don't overlap (can happen when len < 6)
    old_names = {r["name"] for r in old_repos}
    new_repos = [r for r in new_repos if r["name"] not in old_names]
    if not new_repos:
        return False

    def score(repo):
        contents = github_client.get_repo_contents(username, repo["name"]) or []
        points = 0
        if repo.get("has_readme") or any(
            f.lower() in {"readme.md", "readme.rst", "readme.txt", "readme"} for f in contents
        ):
            points += 1
        # Directories appear in contents listing from the API as type "dir";
        # get_repo_contents returns names only, so we proxy depth via the
        # presence of common top-level directories.
        dir_like = {"src", "lib", "app", "components", "utils", "tests", "docs"}
        if any(f in dir_like for f in contents):
            points += 1
        if len(contents) > 5:
            points += 1
        return points

    old_avg = sum(score(r) for r in old_repos) / len(old_repos)
    new_avg = sum(score(r) for r in new_repos) / len(new_repos)
    return new_avg > old_avg


def _bio_signals(user_data) -> bool:
    company = (user_data.get("company") or "").strip()
    bio = (user_data.get("bio") or "").strip()

    if not company and not bio:
        return True

    bio_words = set(re.findall(r"\w+", bio.lower()))
    return bool(bio_words & BIO_INDIE_TERMS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Split on non-alphanumeric characters and return lowercase tokens > 2 chars."""
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) > 2]
