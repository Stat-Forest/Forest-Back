import logging

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled):
        request = context.get("request")
        path = request.path if request else ""
        user = getattr(request, "user", None)

        wait_seconds = getattr(exc, "wait", None) or 0
        wait_minutes = round(wait_seconds / 60, 1)
        wait_hours = round(wait_seconds / 3600, 1)

        # Log 429 for debugging (helps track which endpoints hit limits)
        logger.warning(
            "[THROTTLED] path=%s user=%s wait=%.0fs",
            path,
            getattr(user, "id", "anon") if user else "anon",
            wait_seconds,
        )

        if "/api/v1/ai/" in path or "/ai/" in path:
            return Response(
                {
                    "error": "Kunlik AI so'rov limiti tugadi.",
                    "retry_after_hours": f"{wait_hours} soat",
                    "message": "Iltimos, keyinroq yoki ertaga yana urinib ko'ring.",
                },
                status=429,
            )

        if "/api/v1/authentications/" in path or "/authentications/" in path:
            return Response(
                {
                    "detail": "Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring.",
                    "retry_after_seconds": wait_seconds,
                    "retry_after_minutes": f"{wait_minutes} daqiqa",
                },
                status=429,
            )

        return Response(
            {
                "detail": "Juda ko'p so'rov yuborildi. Iltimos, bir oz kutib, qayta urinib ko'ring.",
                "retry_after_seconds": wait_seconds,
                "retry_after_minutes": f"{wait_minutes} daqiqa",
            },
            status=429,
        )

    return response
