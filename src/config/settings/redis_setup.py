import os

REDIS_CACHE_HOST = os.environ.get("REDIS_HOST", "forest_redis")
REDIS_CACHE_PORT = os.environ.get("REDIS_PORT", "6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_CACHE_HOST}:{REDIS_CACHE_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
