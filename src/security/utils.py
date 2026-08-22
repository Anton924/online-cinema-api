import secrets


def generate_secure_token(length: int = 34) -> str:
    return secrets.token_urlsafe(length)
