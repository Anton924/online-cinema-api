import re

import email_validator


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lower letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[@$!%*?&#]", password):
        raise ValueError("Password must contain at least one special character: @, $, !, %, *, ?, #, &.")
    return password


def validate_email(email: str) -> str:
    try:
        email_validator.validate_email(email, check_deliverability=False)
    except email_validator.EmailNotValidError as error:
        raise ValueError(str(error)) from error
    else:
        return email
