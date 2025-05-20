import os
import requests

from apps.base.exceptions.exception_files import CustomExceptionError

MY_GOV_CHECK_SIGNATURE = "https://sso.my.gov.uz/api/check-signature"

def verify_signature_with_my_gov(signature: str, sign_data: str, pinfl: str):
    token = os.getenv("EXAMPLE")
    if not token:
        raise CustomExceptionError(code=400, detail="MY_GOV_TOKEN was not found in env.")

    headers = {
        "Authorization": f"Bearer: {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "signature": signature,
        "signData": sign_data,
        "pinfl": pinfl
    }

    response = requests.post(MY_GOV_CHECK_SIGNATURE, json=payload, headers=headers)

    if not response:
        raise CustomExceptionError(code=400, detail=f"MyGov check-signature failed: {response.status_code} - {response.text}")
    return response.json()