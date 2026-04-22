import hashlib
import secrets


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("ascii"), 120_000)
    return f"{salt}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    if not stored:
        return False
    try:
        salt, hexd = str(stored).strip().split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("ascii"), 120_000)
    return secrets.compare_digest(dk.hex(), hexd.strip())
