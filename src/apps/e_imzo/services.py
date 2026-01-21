# services.py
import requests

EIMZO_VERIFY_URL = "http://127.0.0.1:8080/backend/auth"


def verify_pkcs7(pkcs7: str) -> dict | None:
    """
    PKCS7 ni E-IMZO backend orqali tekshiradi.
    vo frontenddan kelsa ham — IGNORE qilinadi.
    """

    try:
        response = requests.post(
            EIMZO_VERIFY_URL,
            data=pkcs7,
            headers={"Content-Type": "text/plain"},
            timeout=10
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None
    print(response.status_code, response.text)
    data = response.json()

    # status == 1 → imzo yaroqli
    if data.get("status") != 1:
        return None

    subject = data["subjectCertificateInfo"]["subjectName"]

    return {
        "CN": subject.get("CN", ""),
        "PINFL": subject.get("1.2.860.3.16.1.2", ""),
        "TIN": subject.get("1.2.860.3.16.1.1", ""),
        "UID": data.get("serialNumber", ""),
    }
