# main entry point

import argparse
import functools
import http.server
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

import config
from classifier import classify_profile
from filters import passes_exclusion_filters
from flags import evaluate_flags
from github_client import GitHubClient
from output import save_results
from readme_analyzer import ReadmeAnalyzer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitHub Scout v2")
    parser.add_argument(
        "--usernames",
        help="Comma-separated list of GitHub usernames to evaluate",
    )
    parser.add_argument(
        "--input-file",
        help="Path to a text file with one username per line",
    )
    parser.add_argument(
        "--discover",
        help="Comma-separated GitHub topics to search for (e.g. 'ai-agent,llm,developer-tools')",
    )
    parser.add_argument(
        "--language",
        help="Filter --discover results by primary repo language (e.g. 'python')",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8080)),
        help="Port to serve the results dashboard on (default: PORT env var or 8080)",
    )
    return parser.parse_args()


def collect_usernames(args: argparse.Namespace, github_client: GitHubClient) -> list[str]:
    usernames: list[str] = []

    if args.discover:
        topics = [t.strip() for t in args.discover.split(",") if t.strip()]
        language = (args.language or "").strip() or None
        logger.info(
            "Discovering users via topic search: %s%s",
            topics,
            f" (language: {language})" if language else "",
        )
        discovered = github_client.search_users_by_topics(topics, language=language)
        logger.info("Discovered %d unique users from topic search", len(discovered))
        usernames.extend(discovered)

    if args.usernames:
        usernames.extend(u.strip() for u in args.usernames.split(",") if u.strip())

    if args.input_file:
        with open(args.input_file, encoding="utf-8") as f:
            usernames.extend(line.strip() for line in f if line.strip())

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for u in usernames:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def _account_age_days(created_at: str) -> int:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).days


def process_username(
    username: str,
    github_client: GitHubClient,
    readme_analyzer: ReadmeAnalyzer,
) -> Optional[dict]:
    logger.info("── Processing @%s", username)

    user_data = github_client.get_user(username)
    if user_data is None:
        logger.warning("  Skipping @%s: could not fetch user data", username)
        return None

    repos = github_client.get_repos(username)

    passed, reason = passes_exclusion_filters(user_data, repos, config)
    if not passed:
        logger.info("  Excluded @%s: %s", username, reason)
        return None

    flags = evaluate_flags(username, user_data, repos, github_client, readme_analyzer, config)
    fired = [k for k, v in flags.items() if v]
    logger.info("  Flags fired: %s", fired if fired else "none")

    profile_type = classify_profile(flags, user_data, config)
    logger.info("  Classification: %s", profile_type)

    return {
        "username":             username,
        "profile_type":         profile_type,
        "flags":                flags,
        "follower_count":       user_data.get("followers", 0),
        "account_age_days":     _account_age_days(user_data["created_at"]),
        "github_url":           f"https://github.com/{username}",
        "classification_reason": _classification_reason(profile_type, flags),
    }


def _classification_reason(profile_type: str, flags: dict) -> str:
    fired = [k for k, v in flags.items() if v]
    if profile_type == "Already Known":
        return "Follower count exceeds ceiling"
    if profile_type == "Active Product Builder":
        return "deployment_signals + recent_commit_velocity + external_engagement all present"
    if profile_type == "Early Trajectory":
        return "complexity_progression + domain_focus_clustering present; no deployment signals yet"
    return f"Insufficient signals; flags fired: {', '.join(fired) or 'none'}"


class _DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/dashboard.html"
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        logger.debug("HTTP %s", format % args)


def start_server(output_dir: str, port: int) -> http.server.HTTPServer:
    os.makedirs(output_dir, exist_ok=True)
    handler = functools.partial(
        _DashboardHandler,
        directory=os.path.abspath(output_dir),
    )
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Dashboard server started on port %d", port)
    return server


def main() -> None:
    args = parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not github_token:
        raise SystemExit("Error: GITHUB_TOKEN not set in environment or .env file")
    if not anthropic_api_key:
        raise SystemExit("Error: ANTHROPIC_API_KEY not set in environment or .env file")

    github_client = GitHubClient(github_token)
    readme_analyzer = ReadmeAnalyzer(anthropic_api_key)

    output_dir = "results"
    start_server(output_dir, args.port)

    if not args.discover and not args.usernames and not args.input_file:
        args.discover = "ai-agent,llm,developer-tools,open-source"
        logger.info("No input source specified — defaulting to --discover %s", args.discover)

    usernames = collect_usernames(args, github_client)
    if not usernames:
        raise SystemExit("Error: no usernames found — use --usernames, --input-file, or --discover")

    logger.info("Evaluating %d username(s)", len(usernames))

    results: list[dict] = []
    for username in usernames:
        result = process_username(username, github_client, readme_analyzer)
        if result is not None:
            results.append(result)

    logger.info("Done. %d/%d profiles passed filters.", len(results), len(usernames))

    save_results(results, output_dir)

    dashboard_path = os.path.abspath(os.path.join(output_dir, "dashboard.html"))
    print(f"\nDashboard: http://localhost:{args.port}/dashboard.html")
    print(f"Local file: {dashboard_path}")

    threading.Event().wait()  # keep process alive so the server keeps running


if __name__ == "__main__":
    main()
