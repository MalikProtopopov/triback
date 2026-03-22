"""Fernet encryption for sensitive data (e.g. bot tokens)."""

from __future__ import annotations

import structlog
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = structlog.get_logger(__name__)


class FernetEncryption:
    """Encrypt/decrypt strings using Fernet (symmetric)."""

    def __init__(self) -> None:
        self._fernet: Fernet | None = None
        if settings.ENCRYPTION_KEY:
            try:
                self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            except Exception as e:
                logger.warning("encryption_key_invalid", error=str(e))
                self._fernet = None
        else:
            logger.warning("encryption_key_missing", hint="Set ENCRYPTION_KEY for token encryption")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext. Returns ciphertext as string, or plaintext if encryption unavailable."""
        if not self._fernet:
            return plaintext
        try:
            return self._fernet.encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.exception("encryption_failed", error=str(e))
            raise

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext. Returns plaintext, or raises InvalidToken if invalid."""
        if not self._fernet:
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as e:
            logger.warning("decryption_failed_invalid_token", error=str(e))
            raise
        except Exception as e:
            logger.exception("decryption_failed", error=str(e))
            raise

    @property
    def is_available(self) -> bool:
        return self._fernet is not None


_encryption: FernetEncryption | None = None


def get_encryption() -> FernetEncryption:
    """Singleton FernetEncryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = FernetEncryption()
    return _encryption
