"""Soxta e-imzo-server (hisobot imzosi testlaridagi bilan bir xil xatti-harakat)."""
import base64
import json

from apps.yashil.services import signing

TIN = "305123456"
PINFL = "31234567890123"


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data, self.status_code, self.text = data, status_code, json.dumps(data)

    def json(self):
        return self._data


def fake_sign(text: str) -> str:
    """Testda imzo = matnning base64 ko'rinishi."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class FakeEimzo:
    CHALLENGE = "9b573e40-cefd-42cc-a534-f6e78b27c2ae"

    def __init__(self, tin=TIN, pinfl=PINFL, status=1, verified=True, tsa_down=False, vpn_up=False, cn="RAIS TEST"):
        self.tin, self.pinfl, self.status, self.verified = tin, pinfl, status, verified
        self.tsa_down, self.vpn_up, self.cn = tsa_down, vpn_up, cn

    def _subject(self):
        subject = {"CN": self.cn, signing.OID_PINFL: self.pinfl}
        if self.tin:
            subject[signing.OID_TIN] = self.tin
        return subject

    def vpn_available(self, request):
        return self.vpn_up

    def eri_challenge(self, request):
        return True, 200, {"challenge": self.CHALLENGE, "ttl": 120, "status": 1}

    def eri_backend_auth(self, request, pkcs7):
        signed_text = base64.b64decode(pkcs7).decode("utf-8")
        if signed_text != self.CHALLENGE:
            return False, 200, "Challenge topilmadi yoki muddati o'tdi. Qaytadan urinib ko'ring."
        cert = {"serialNumber": "abc123", "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00",
                "subjectName": self._subject()}
        return True, 200, {"status": 1 if self.vpn_up else -1, "subjectCertificateInfo": cert}

    def pkcs7_info(self, pkcs7, request):
        return 200, FakeResponse({"signers": [{"certificate": [{
            "subjectInfo": self._subject(), "serialNumber": "abc123",
            "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00"}]}]})

    def timestamp_pkcs7(self, pkcs7, request):
        if self.tsa_down:
            return 400, FakeResponse({"status": -1, "message": "TimeStampTokenProvider UNAVAILABLE"}, 400)
        return 200, FakeResponse({"status": 1, "pkcs7b64": pkcs7, "message": ""})

    def eimzo_verify(self, pkcs7, request):
        return 200, FakeResponse({
            "status": self.status,
            "message": "" if self.status == 1 else "ЭЦП недействительна",
            "pkcs7Info": {
                "documentBase64": pkcs7,
                "signers": [{
                    "signingTime": "2026-10-05 12:00:00", "verified": self.verified,
                    "certificateVerified": True, "certificateValidAtSigningTime": True,
                    "timeStampInfo": {"time": "2026-10-05 12:00:05", "verified": True, "tsa": "test-tsa"},
                    "certificate": [{"subjectInfo": self._subject(), "serialNumber": "abc123",
                                     "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00",
                                     "issuerName": "CN=TestCA"}],
                }],
            },
        })
