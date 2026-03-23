"""TTL and limits for guest email verification."""

VERIFY_TTL = 600
MAX_ATTEMPTS = 5
MAX_SENDS = 3


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    masked_local = local if len(local) <= 1 else local[0] + "***"
    return f"{masked_local}@{domain}"
