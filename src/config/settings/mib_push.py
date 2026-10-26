import os

# MIB Push Service (pushservice.egov.uz): ijara shartnomalari o'zgarganda MIB'ga yuboriladi.
# billing-urmon.uz dagi integratsiya bilan bir xil tizim nomi va RSA kalit ishlatiladi —
# egov'da qayta ro'yxatdan o'tish shart emas. Kalit gitda emas: serverda
# /root/Forest-Back/keys/mib/private.pem, konteynerlarga /etc/mib-push ga mount qilinadi.
MIB_PUSH = {
    "ENABLED": os.getenv("MIB_PUSH_ENABLED", "False") == "True",
    "BASE_URL": os.getenv("MIB_PUSH_BASE_URL", "https://pushservice.egov.uz"),
    "PRIVATE_KEY_PATH": os.getenv("MIB_PUSH_PRIVATE_KEY_PATH", "/etc/mib-push/private.pem"),
    "SYSTEM_NAME": os.getenv("MIB_PUSH_SYSTEM_NAME", "billing-urmon"),
    "SUBSCRIBERS": [s.strip() for s in os.getenv("MIB_PUSH_SUBSCRIBERS", "tashqi_manbaa_at").split(",") if s.strip()],
    "TOKEN_EXPIRY": int(os.getenv("MIB_PUSH_TOKEN_EXPIRY", 3600)),
    "TIMEOUT": int(os.getenv("MIB_PUSH_TIMEOUT", 10)),
    "DTL_DAYS": int(os.getenv("MIB_PUSH_DTL_DAYS", 10)),
    "MAX_ATTEMPTS": int(os.getenv("MIB_PUSH_MAX_ATTEMPTS", 5)),
}
