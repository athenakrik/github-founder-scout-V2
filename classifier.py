# Layer 3: categorical classification


def classify_profile(flags: dict, user_data: dict, config) -> str:
    if user_data["followers"] > config.FOLLOWER_CEILING:
        return "Already Known"

    if flags["deployment_signals"] and flags["recent_commit_velocity"] and flags["external_engagement"]:
        return "Active Product Builder"

    if flags["complexity_progression"] and flags["domain_focus_clustering"] and not flags["deployment_signals"]:
        return "Early Trajectory"

    return "Hobbyist"
