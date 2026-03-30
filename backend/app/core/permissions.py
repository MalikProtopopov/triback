"""Role → sidebar sections mapping for admin and client frontends."""

# Admin sidebar keys (staff roles)
_ADMIN_SIDEBAR = {
    "admin": [
        "dashboard",
        "doctors",
        "protocol_history",
        "doctors_import",
        "events",
        "payments",
        "arrears",
        "content",
        "content_articles",
        "content_themes",
        "content_documents",
        "settings",
        "settings_general",
        "settings_cities",
        "settings_plans",
        "settings_seo",
        "voting",
        "notifications",
        "portal_users",
        "administrators",
    ],
    "manager": [
        "dashboard",
        "doctors",
        "protocol_history",
        "events",
        "payments",
        "content",
        "content_articles",
        "content_themes",
        "content_documents",
        "settings",
        "settings_cities",
        "notifications",
        "portal_users",
    ],
    "accountant": [
        "payments",
        "arrears",
        "doctors",
        "protocol_history",
    ],
}

# Client cabinet sidebar keys (doctor, user)
_CLIENT_SIDEBAR = {
    "doctor": [
        "cabinet",
        "personal",
        "public",
        "payments",
        "events",
        "certificate",
        "telegram",
        "settings",
        "voting",
    ],
    "user": [
        "cabinet",
        "events",
        "telegram",
        "settings",
    ],
    # No DB role yet — only email verified; must complete onboarding / choose role
    "pending": [
        "cabinet",
        "settings",
    ],
}


def get_sidebar_sections_for_role(role: str) -> list[str]:
    """Return sidebar section keys for the given role.

    Staff roles (admin, manager, accountant) get admin sidebar keys.
    Portal roles (doctor, user) get client cabinet keys.
    Unknown roles get minimal client sidebar (cabinet, settings).
    """
    if role in _ADMIN_SIDEBAR:
        return _ADMIN_SIDEBAR[role].copy()
    if role in _CLIENT_SIDEBAR:
        return _CLIENT_SIDEBAR[role].copy()
    return ["cabinet", "settings"]
