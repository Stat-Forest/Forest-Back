# services.py
import requests

EIMZO_VERIFY_URL = "http://127.0.0.1:8080/backend/auth"


def verify_pkcs7(pkcs7: str) -> dict | None:
    try:
        response = requests.post(
            EIMZO_VERIFY_URL,
            json={"pkcs7": pkcs7},  # ❗ JSON formatida yuborish
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(response.status_code, response.text,'Tekshiriuv !!!')
    except requests.RequestException as e:
        print("RequestException:", e)
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    if data.get("status") != 1:
        print("Status noto‘g‘ri:", data.get("status"))
        return None

    subject = data["subjectCertificateInfo"]["subjectName"]

    return {
        "CN": subject.get("CN", ""),
        "PINFL": subject.get("1.2.860.3.16.1.2", ""),
        "TIN": subject.get("1.2.860.3.16.1.1", ""),
        "UID": data.get("serialNumber", ""),
    }

