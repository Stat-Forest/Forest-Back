import json
import hashlib
from typing import Any, Callable, Dict, Optional

from django.core.cache import cache


def _hash_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def get_cache_version(version_key: str, default: int = 1) -> int:
    v = cache.get(version_key)
    return int(v) if v is not None else default


def bump_cache_version(version_key: str) -> int:
    try:
        return cache.incr(version_key)
    except Exception:
        cache.set(version_key, 2, timeout=None)
        return 2


def build_list_cache_key(
    *,
    namespace: str,
    request,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    user = request.user
    lang = request.query_params.get("lang", "uz")

    qp = {k: request.query_params.getlist(k) for k in request.query_params.keys()}

    payload = {
        "lang": lang,
        "query_params": qp,
        "user_id": getattr(user, "id", None),
        "role": getattr(user, "role", None),
        "org_id": getattr(getattr(user, "organization", None), "id", None),
        "statement_id": getattr(getattr(user, "statement", None), "id", None),
    }

    if extra:
        payload.update(extra)

    hashed = _hash_payload(payload)
    return f"{namespace}:{hashed}"


def cache_get_or_set(
    *,
    key: str,
    version: int,
    ttl: int,
    compute: Callable[[], Any],
    lock_ttl: int = 10,
) -> Any:
    full_key = f"v{version}:{key}"

    cached = cache.get(full_key)
    if cached is not None:
        return cached

    lock_key = f"lock:{full_key}"
    got_lock = cache.add(lock_key, "1", timeout=lock_ttl)

    if got_lock:
        try:
            result = compute()
            cache.set(full_key, result, timeout=ttl)
            return result
        finally:
            cache.delete(lock_key)

    # fallback: parallel so‘rovlar kutmaydi
    return compute()
