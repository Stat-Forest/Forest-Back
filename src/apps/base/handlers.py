from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled) and response is not None:
        wait_seconds = getattr(exc, 'wait', 0)
        wait_hours = round(wait_seconds / 3600, 1)

        response.data = {
            "error": "Kunlik AI so‘rov limiti tugadi.",
            "retry_after_hours": f"{wait_hours} soat",
            "message": "Iltimos, keyinroq yoki ertaga yana urinib ko‘ring."
        }

    return response