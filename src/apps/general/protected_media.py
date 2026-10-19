"""
Himoyalangan media fayllar (yer hujjatlari, rezyumelar, ma'lumotnomalar).

Kiberxavfsizlik markazi topilmasi (CWE-200, 13-rasm): /media/ ostidagi
fayllar URL'ni bilgan har kimga login'siz ochilardi. Endi:

  * API javobidagi `file_url` imzolangan va muddatli: /media/<path>?t=<token>
    (token = signing.dumps({"p": path}), PROTECTED_MEDIA_URL_TTL soniya).
  * nginx /media/documents|resumes|handbooks/ so'rovlarini Django'ga
    (ProtectedMediaView) yo'naltiradi; Django tokenni (yoki admin
    sessiyasini) tekshirib, faylni X-Accel-Redirect bilan nginx orqali beradi
    — fayl oqimi Django'dan o'tmaydi.
  * Qolgan media (e'lon rasmlari, shakl ikonkalari, profil rasmlari) avvalgidek
    ochiq.
"""
import mimetypes
import os
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.views import View

SALT = "protected-media"
# legacy_billing/: eski billing importi manbasi (ijarachilar PII) — ochiq bo'lmasin (audit C14)
DEFAULT_PREFIXES = ("documents/", "resumes/", "handbooks/", "legacy_billing/")
# nginx: location /protected-media/ { internal; alias /app/media/; }
ACCEL_PREFIX = "/protected-media/"


def protected_prefixes():
    return getattr(settings, "PROTECTED_MEDIA_PREFIXES", DEFAULT_PREFIXES)


def url_ttl() -> int:
    return int(getattr(settings, "PROTECTED_MEDIA_URL_TTL", 3600))


def is_protected(name: str) -> bool:
    return any(name.startswith(p) for p in protected_prefixes())


def make_token(name: str) -> str:
    return signing.dumps({"p": name}, salt=SALT, compress=True)


def verify_token(token: str, name: str) -> bool:
    try:
        data = signing.loads(token, salt=SALT, max_age=url_ttl())
    except signing.BadSignature:
        return False
    return data.get("p") == name


def signed_file_url(request, file_field) -> str | None:
    """Serializer'lar uchun: himoyalangan faylga imzolangan absolute URL."""
    if not file_field or not getattr(file_field, "name", None):
        return None
    url = file_field.url
    if is_protected(file_field.name):
        url = f"{url}?t={quote(make_token(file_field.name))}"
    return request.build_absolute_uri(url) if request else url


class ProtectedMediaView(View):
    """
    GET /media/<path>?t=<token>

    Ruxsat: to'g'ri va muddati o'tmagan token, yoki admin (is_staff) sessiyasi
    (Django admin'dagi fayl havolalari uchun).
    """

    def get(self, request, path: str):
        if ".." in path.split("/") or path.startswith("/"):
            raise Http404

        user = getattr(request, "user", None)
        is_staff = bool(user and user.is_authenticated and user.is_staff)
        token = request.GET.get("t", "")
        if not is_staff and not (token and verify_token(token, path)):
            return HttpResponseForbidden("Faylga kirish uchun ruxsat yo'q yoki havola muddati o'tgan.")

        full_path = os.path.join(settings.MEDIA_ROOT, path)
        if not os.path.isfile(full_path):
            raise Http404

        filename = os.path.basename(path)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        disposition = f"attachment; filename*=UTF-8''{quote(filename)}"

        if getattr(settings, "PROTECTED_MEDIA_SERVE_DIRECTLY", settings.DEBUG):
            # Lokal ishlab chiqish: nginx yo'q, faylni Django'ning o'zi beradi
            response = FileResponse(open(full_path, "rb"), content_type=content_type)
        else:
            response = HttpResponse(content_type=content_type)
            response["X-Accel-Redirect"] = ACCEL_PREFIX + quote(path)
        response["Content-Disposition"] = disposition
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
