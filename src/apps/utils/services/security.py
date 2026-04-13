import hashlib
import hmac
from typing import Optional


def hash_reset_code(email: str, code: str) -> str:
    value = f"{email.strip().lower()}:{code.strip()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_equal(val1: Optional[str], val2: Optional[str]) -> bool:
    return hmac.compare_digest(val1 or "", val2 or "")