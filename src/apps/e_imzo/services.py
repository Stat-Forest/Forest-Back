# src/apps/e_imzo/services.py
import requests
from rest_framework.request import Request


class EimzoServiceApi:
    def __init__(self):
        self.VERIFY_URL = "http://e_imzo_server:8080/backend/pkcs7/verify"
        self.JOIN_URL = "http://e_imzo_server:8080/frontend/pkcs7/join"
        self.TIME_STAMP_URL = "http://e_imzo_server:8080/frontend/timestamp/pkcs7"
        self.CHALLENGE_URL = "http://e_imzo_server:8080/frontend/challenge"
        self.BACKEND_AUTH_URL = "http://e_imzo_server:8080/backend/auth"

    @staticmethod
    def get_user_ip(request: Request) -> str:
        return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "Unknown"

    def get_headers(self, request: Request) -> dict:
        return {"X-Real-IP": self.get_user_ip(request)}

    def timestamp_pkcs7(self, pkcs7: str, request: Request):
        res = requests.post(self.TIME_STAMP_URL, data=pkcs7, headers=self.get_headers(request))
        return res.status_code, res

    def eimzo_verify(self, pkcs7wtst: str, request: Request):
        res = requests.post(f"{self.VERIFY_URL}/attached", data=pkcs7wtst, headers=self.get_headers(request))
        return res.status_code, res

    def pkcs7_join(self, pkcs7_data_1: str, pkcs7_data_2: str, request: Request):
        data = f"{pkcs7_data_1}|{pkcs7_data_2}"
        res = requests.post(self.JOIN_URL, data=data, headers=self.get_headers(request))
        return res.status_code, res

    def eri_challenge(self, request: Request):
        res = requests.get(self.CHALLENGE_URL, headers=self.get_headers(request))
        if res.status_code != 200:
            return False, res.status_code, res.json()
        return True, res.status_code, res.json()

    def eri_backend_auth(self, request: Request, pkcs7: str):
        res = requests.post(self.BACKEND_AUTH_URL, headers=self.get_headers(request), data=pkcs7)
        if res.status_code != 200:
            return False, res.status_code, res.text
        data = res.json()
        success_status = data.get("status")

        # 1  = to'liq muvaffaqiyat (OCSP ishladi)
        # -1 = OCSP ishlamadi, lekin imzo va sertifikat VERIFIED — qabul qilamiz
        if success_status not in (1, -1):
            err_messages = {
                -5: "Imzo vaqti noto'g'ri. Kompyuter vaqtini tekshiring.",
                -10: "ERI noto'g'ri.",
                -11: "Sertifikat noto'g'ri.",
                -12: "Sertifikat imzo sanasida noto'g'ri.",
                -20: "Challenge topilmadi yoki muddati o'tdi. Qaytadan urinib ko'ring.",
            }
            msg = err_messages.get(success_status, "Noma'lum xatolik.")
            return False, res.status_code, msg

        return True, res.status_code, data