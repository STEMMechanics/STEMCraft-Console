import pyotp

from app.tfa import (
    generate_totp_secret,
    hash_recovery_code,
    verify_totp,
)


def test_generate_totp_secret():

    secret = generate_totp_secret()

    assert secret
    assert len(secret) >= 16


def test_valid_totp():

    secret = generate_totp_secret()

    code = pyotp.TOTP(
        secret
    ).now()

    assert verify_totp(
        secret,
        code,
    )


def test_invalid_totp():

    secret = generate_totp_secret()

    assert not verify_totp(
        secret,
        "000000",
    )


def test_recovery_code_normalisation():

    assert (
        hash_recovery_code(
            "ABCDE-12345"
        )
        ==
        hash_recovery_code(
            "abcde12345"
        )
    )