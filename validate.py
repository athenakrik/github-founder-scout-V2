# ground truth validation — runs the pipeline against known accounts

import logging
import os

from dotenv import load_dotenv

import config
from classifier import classify_profile
from filters import passes_exclusion_filters
from flags import evaluate_flags
from github_client import GitHubClient
from readme_analyzer import ReadmeAnalyzer

load_dotenv()

logging.basicConfig(level=logging.WARNING)  # suppress pipeline noise during validation

# ---------------------------------------------------------------------------
# Ground truth buckets
# ---------------------------------------------------------------------------

# Builders you know personally ship real products — expected to PASS filters
# and land in "Active Product Builder" or "Early Trajectory".
bucket_1_expected_pass: list[str] = []  # fill in manually

# Additional known good builders — expected to pass.
bucket_2_expected_pass: list[str] = []  # fill in manually

# High-profile / corporate accounts — expected to be EXCLUDED by filters
# or classified as "Already Known".
bucket_3_expected_fail: list[str] = ["torvalds", "karpathy"]


# ---------------------------------------------------------------------------
# Expectation definitions
# ---------------------------------------------------------------------------

PASS_CLASSIFICATIONS = {"Active Product Builder", "Early Trajectory", "Hobbyist"}
FAIL_CLASSIFICATIONS = {"Already Known"}
FAIL_ALSO_VIA_FILTER = True  # excluded-by-filter also counts as a "fail" expectation met


def run_pipeline(username: str, github_client: GitHubClient, readme_analyzer: ReadmeAnalyzer) -> dict:
    """Run the full pipeline for one username. Returns a result dict."""
    user_data = github_client.get_user(username)
    if user_data is None:
        return {"username": username, "status": "error", "detail": "could not fetch user data"}

    repos = github_client.get_repos(username)
    passed_filters, reason = passes_exclusion_filters(user_data, repos, config)

    if not passed_filters:
        return {"username": username, "status": "excluded", "detail": reason}

    flags = evaluate_flags(username, user_data, repos, github_client, readme_analyzer, config)
    profile_type = classify_profile(flags, user_data, config)
    return {"username": username, "status": "classified", "profile_type": profile_type, "flags": flags}


def check_pass_expectation(result: dict) -> tuple[bool, str]:
    """Return (ok, note) for a username expected to pass filters and be classified."""
    if result["status"] == "error":
        return False, f"pipeline error — {result['detail']}"
    if result["status"] == "excluded":
        return False, f"unexpectedly excluded — {result['detail']}"
    pt = result["profile_type"]
    if pt in PASS_CLASSIFICATIONS:
        return True, f"classified as '{pt}'"
    return False, f"classified as '{pt}' (expected a pass classification)"


def check_fail_expectation(result: dict) -> tuple[bool, str]:
    """Return (ok, note) for a username expected to fail (be excluded or Already Known)."""
    if result["status"] == "error":
        return False, f"pipeline error — {result['detail']}"
    if result["status"] == "excluded":
        return True, f"correctly excluded — {result['detail']}"
    pt = result["profile_type"]
    if pt in FAIL_CLASSIFICATIONS:
        return True, f"correctly classified as '{pt}'"
    return False, f"classified as '{pt}' — expected exclusion or 'Already Known'"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_bucket(
    label: str,
    usernames: list[str],
    expect_pass: bool,
    github_client: GitHubClient,
    readme_analyzer: ReadmeAnalyzer,
) -> tuple[int, int]:
    """Run validation for one bucket. Returns (passed, total)."""
    if not usernames:
        print(f"\n{label}: (empty — skipping)\n")
        return 0, 0

    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")

    passed = 0
    for username in usernames:
        result = run_pipeline(username, github_client, readme_analyzer)
        checker = check_pass_expectation if expect_pass else check_fail_expectation
        ok, note = checker(result)
        status_icon = "✓" if ok else "✗"
        print(f"  {status_icon} @{username:<20} {note}")
        if ok:
            passed += 1

    return passed, len(usernames)


def main() -> None:
    github_token = os.environ.get("GITHUB_TOKEN")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not github_token:
        raise SystemExit("Error: GITHUB_TOKEN not set in environment or .env file")
    if not anthropic_api_key:
        raise SystemExit("Error: ANTHROPIC_API_KEY not set in environment or .env file")

    github_client = GitHubClient(github_token)
    readme_analyzer = ReadmeAnalyzer(anthropic_api_key)

    buckets = [
        ("Bucket 1 — known builders (expect: pass)",   bucket_1_expected_pass, True),
        ("Bucket 2 — known builders (expect: pass)",   bucket_2_expected_pass, True),
        ("Bucket 3 — high-profile (expect: excluded)", bucket_3_expected_fail, False),
    ]

    total_passed = 0
    total_cases = 0

    for label, usernames, expect_pass in buckets:
        p, t = run_bucket(label, usernames, expect_pass, github_client, readme_analyzer)
        total_passed += p
        total_cases += t

    print(f"\n{'═' * 60}")
    if total_cases == 0:
        print("  No test cases ran — add usernames to the buckets.")
    else:
        pct = round(100 * total_passed / total_cases)
        result_line = f"  RESULT: {total_passed}/{total_cases} passed ({pct}%)"
        overall = "PASS" if total_passed == total_cases else "FAIL"
        print(f"{result_line}  [{overall}]")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
