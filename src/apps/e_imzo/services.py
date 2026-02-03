# apps/e_imzo/services.py
import requests
from django.conf import settings


EIMZO_VERIFY_URL = settings.EIMZO_VERIFY_URL  # http://e-imzo-server:8080/backend/auth


def verify_pkcs7(pkcs7: str) -> dict | None:
    try:
        response = requests.post(
            EIMZO_VERIFY_URL,
            json={"pkcs7": pkcs7},
            timeout=10
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # E-imzo server odatda shunaqa qaytaradi
        # { "success": true, "vo": {...} }
        if not data.get("success"):
            return None

        return data.get("vo") or None

    except Exception:
        return None
