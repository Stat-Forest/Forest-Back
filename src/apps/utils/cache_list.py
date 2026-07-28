import json, time, hashlib

from typing import Any, Callable, Dict, Optional

from django.core.cache import cache

from apps.reports.services.report_cache import get_report_list_version


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


def build_list_cache_key(*, namespace: str, request) -> str:
    user = request.user

    qp = {
        k: sorted(request.query_params.getlist(k))
        for k in sorted(request.query_params.keys())
    }

    payload = {
        "user_id": user.id,
        "role": user.role,
        "org_id": getattr(user.organization, "id", None),
        "lang": request.query_params.get("lang", "uz"),
        "query_params": qp,
    }

    raw = json.dumps(payload, sort_keys=True, default=str)
    hashed = hashlib.sha1(raw.encode()).hexdigest()

    return f"{namespace}:{hashed}"




def cache_get_or_set(
    *,
    key: str,
    version: int,
    ttl: int,
    compute: Callable[[], Any],
    lock_ttl: int = 10,
    wait_timeout: float = 0.3,
) -> Any:
    full_key = f"v{version}:{key}"

    cached = cache.get(full_key)
    if cached is not None:
        return cached

    lock_key = f"lock:{full_key}"

    if cache.add(lock_key, "1", timeout=lock_ttl):
        try:
            result = compute()
            cache.set(full_key, result, timeout=ttl)
            return result
        except Exception:
            raise
        finally:
            cache.delete(lock_key)

    time.sleep(wait_timeout)
    cached = cache.get(full_key)
    if cached is not None:
        return cached

    return compute()


