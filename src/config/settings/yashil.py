import os

# «Yashil mahalla»: muhitga bog'liq sozlamalar (docs/yashil/sozlamalar-pasporti.md)
# QR tekshirish havolasi shu domenga yoziladi — test serverda o'z domeni bo'lishi kerak
YASHIL_PUBLIC_BASE_URL = os.getenv("YASHIL_PUBLIC_BASE_URL", "https://stat-urmon.uz")
# True — imzoga vaqt tamg'asi (TSA) qo'shilmasa imzo qabul qilinmaydi (D-2: VPN kaliti yangilangach)
EIMZO_REQUIRE_TIMESTAMP = os.getenv("EIMZO_REQUIRE_TIMESTAMP", "False") == "True"
