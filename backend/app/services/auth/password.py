
from pwdlib import PasswordHash


# Use the recommended password hashing algorithm.
# With the Argon2 extra installed, this selects Argon2.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the recommended
    secure password hashing algorithm.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against its stored hash.
    Returns True when the password matches.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )
