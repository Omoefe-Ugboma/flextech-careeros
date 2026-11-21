
from app.services.auth.password import (
    hash_password,
    verify_password,
)


def test_hash_password_returns_different_value():
    password = "TestPassword123"

    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)


def test_correct_password_is_verified():
    password = "TestPassword123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_wrong_password_is_rejected():
    hashed = hash_password("TestPassword123")

    assert verify_password(
        "WrongPassword456",
        hashed,
    ) is False


def test_same_password_generates_different_hashes():
    password = "TestPassword123"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True
