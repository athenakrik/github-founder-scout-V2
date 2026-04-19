# Layer 1: hard exclusion logic

from datetime import datetime, timezone


def passes_exclusion_filters(user_data: dict, repos: list, config) -> tuple[bool, str]:
    # 1. Organization accounts
    if user_data.get("type") == "Organization":
        return False, "organization account"

    # 2. Corporate employer in company field
    company = (user_data.get("company") or "").strip().lower()
    if any(employer.lower() in company for employer in config.CORPORATE_EMPLOYERS):
        return False, "employed at major tech company"

    # 3. Corporate language in bio
    bio = (user_data.get("bio") or "").lower()
    if any(term in bio for term in config.CORPORATE_BIO_TERMS):
        return False, "corporate bio language detected"

    # 4. No original repos
    if not repos:
        return False, "no original repos"

    # 5. Account age
    created_at = datetime.fromisoformat(
        user_data["created_at"].replace("Z", "+00:00")
    )
    age_days = (datetime.now(timezone.utc) - created_at).days
    if age_days < config.ACCOUNT_MIN_AGE_DAYS:
        return False, "account too new"

    return True, ""
