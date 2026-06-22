from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path


ENCRYPTED_PREFIX = "enc:v1:"
SECRET_ENV = "FOCUSAWAY_SECRET_KEY"
SECRET_FILE_ENV = "FOCUSAWAY_SECRET_KEY_FILE"
DEFAULT_SECRET_FILE_NAME = "focusaway-secret.key"


def is_encrypted(value: str) -> bool:
    return str(value or "").startswith(ENCRYPTED_PREFIX)


def encrypt_text(value: str, config_path: Path) -> str:
    if not value or is_encrypted(value):
        return value
    master_key = master_secret(config_path)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = derive_keys(master_key, salt)
    plaintext = value.encode("utf-8")
    ciphertext = xor_bytes(plaintext, key_stream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return ENCRYPTED_PREFIX + ":".join(
        b64encode(part)
        for part in (
            salt,
            nonce,
            ciphertext,
            tag,
        )
    )


def decrypt_text(value: str, config_path: Path) -> str:
    if not value or not is_encrypted(value):
        return value
    parts = value[len(ENCRYPTED_PREFIX) :].split(":")
    if len(parts) != 4:
        raise ValueError("Encrypted secret format is invalid.")
    salt, nonce, ciphertext, expected_tag = (b64decode(part) for part in parts)
    master_key = master_secret(config_path)
    enc_key, mac_key = derive_keys(master_key, salt)
    actual_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(actual_tag, expected_tag):
        raise ValueError("Encrypted secret could not be verified. Check FOCUSAWAY_SECRET_KEY or the local secret key file.")
    plaintext = xor_bytes(ciphertext, key_stream(enc_key, nonce, len(ciphertext)))
    return plaintext.decode("utf-8")


def master_secret(config_path: Path) -> bytes:
    env_secret = os.environ.get(SECRET_ENV, "").strip()
    if env_secret:
        return normalize_secret(env_secret)

    path = secret_file_path(config_path)
    if path.exists():
        return normalize_secret(path.read_text(encoding="utf-8").strip())

    path.parent.mkdir(parents=True, exist_ok=True)
    raw_secret = b64encode(secrets.token_bytes(32))
    path.write_text(raw_secret + "\n", encoding="utf-8")
    secure_file(path)
    return normalize_secret(raw_secret)


def secret_file_path(config_path: Path) -> Path:
    configured = os.environ.get(SECRET_FILE_ENV, "").strip()
    if configured:
        return Path(configured)
    return config_path.parent / DEFAULT_SECRET_FILE_NAME


def normalize_secret(value: str) -> bytes:
    try:
        decoded = b64decode(value)
        if len(decoded) >= 32:
            return decoded
    except ValueError:
        pass
    return hashlib.sha256(value.encode("utf-8")).digest()


def derive_keys(master_key: bytes, salt: bytes) -> tuple[bytes, bytes]:
    material = hashlib.pbkdf2_hmac("sha256", master_key, salt, 200_000, dklen=64)
    return material[:32], material[32:]


def key_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def secure_file(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
