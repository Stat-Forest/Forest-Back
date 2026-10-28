"""
/admin/ va /billing-admin/ uchun IP allowlist (audit 2026-10-27, "admin internetga ochiq").

Sozlama: .env -> ADMIN_ALLOWED_IPS="203.0.113.5,198.51.100.0/24" (vergul bilan, IP yoki CIDR).
Bo'sh bo'lsa cheklov YO'Q (hozirgidek ochiq) — noto'g'ri sozlama bilan admin'dan
butunlay ajralib qolmaslik uchun. Mijoz IP'si nginx qo'ygan X-Real-IP'dan olinadi
(app porti tashqariga ochiq emas, header'ni faqat nginx qo'yadi); u bo'lmasa REMOTE_ADDR.
"""
import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

PROTECTED_PREFIXES = ("/admin/", "/billing-admin/")


def parse_networks(raw):
    """"1.2.3.4, 10.0.0.0/8" -> [ip_network, ...]; noto'g'ri yozuvlar log bilan tashlab yuboriladi."""
    networks = []
    for item in (raw or "").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            logger.error("ADMIN_ALLOWED_IPS: noto'g'ri qiymat o'tkazib yuborildi: %r", item)
    return networks


def client_ip(request):
    ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if not ip:
        ip = (request.META.get("REMOTE_ADDR") or "").strip()
    return ip


class AdminIPAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(PROTECTED_PREFIXES):
            networks = parse_networks(getattr(settings, "ADMIN_ALLOWED_IPS", ""))
            if networks:
                ip = client_ip(request)
                try:
                    addr = ipaddress.ip_address(ip)
                    allowed = any(addr in net for net in networks)
                except ValueError:
                    allowed = False
                if not allowed:
                    logger.warning("Admin IP allowlist: %s -> %s rad etildi", ip or "?", path)
                    return HttpResponseForbidden("Bu manzilga kirish faqat ruxsat etilgan IP'lardan.")
        return self.get_response(request)
