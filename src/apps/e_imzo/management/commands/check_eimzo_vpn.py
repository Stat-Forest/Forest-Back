"""
E-imzo VPN holati va VPN kalit muddatini tekshiradi.

Cron (host, har kuni):
    0 8 * * * docker exec forest_app_prod python manage.py check_eimzo_vpn >> /var/log/eimzo_check.log 2>&1

VPN ulanmasa yoki kalit muddatiga 14 kundan kam qolsa exit code 1 va
(EIMZO_ALERT_EMAIL berilgan bo'lsa) email yuboradi. Kalit muddati
tugab qolgani 2026-yil yanvardan oktabrgacha sezilmay yurgan — shu
takrorlanmasligi uchun.
"""
import os
from datetime import datetime

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

INFO_URL = "http://e_imzo_server:8080/info"
PING_URL = "http://e_imzo_server:8080/ping"
WARN_DAYS = 14


class Command(BaseCommand):
    help = "E-imzo VPN ulanishi va VPN kalit muddatini tekshiradi"

    def add_arguments(self, parser):
        parser.add_argument("--warn-days", type=int, default=WARN_DAYS)

    def handle(self, *args, **options):
        problems = []

        try:
            ping = requests.get(PING_URL, timeout=(5, 20))
            ping_ok = ping.status_code == 200 and "vpnKeyInfo" in ping.text
            if not ping_ok:
                problems.append(f"VPN ulanmadi: {ping.text[:200]}")
        except requests.RequestException as exc:
            problems.append(f"e-imzo-server javob bermadi (/ping): {exc}")

        key_info = {}
        try:
            info = requests.get(INFO_URL, timeout=(5, 20)).json()
            key_info = info.get("vpnKeyInfo") or {}
        except (requests.RequestException, ValueError) as exc:
            problems.append(f"/info o'qilmadi: {exc}")

        valid_to = key_info.get("validTo")
        if valid_to:
            try:
                expires = datetime.strptime(valid_to, "%Y.%m.%d %H:%M:%S")
                days_left = (expires - datetime.now()).days
                self.stdout.write(f"VPN kalit: CN={key_info.get('subjectInfo', {}).get('CN')} validTo={valid_to} ({days_left} kun qoldi)")
                if days_left < 0:
                    problems.append(f"VPN kalit muddati TUGAGAN: {valid_to}")
                elif days_left < options["warn_days"]:
                    problems.append(f"VPN kalit muddati tugayapti: {valid_to} ({days_left} kun qoldi) — NIC NT dan yangisini so'rang")
            except ValueError:
                problems.append(f"validTo formati noma'lum: {valid_to}")
        else:
            problems.append("/info da vpnKeyInfo yo'q — VPN kalit yuklanmagan")

        stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        if not problems:
            self.stdout.write(self.style.SUCCESS(f"[{stamp}] E-imzo VPN OK"))
            return

        for p in problems:
            self.stderr.write(self.style.ERROR(f"[{stamp}] {p}"))

        alert_to = os.environ.get("EIMZO_ALERT_EMAIL")
        if alert_to:
            try:
                send_mail(
                    "STAT-URMON: E-imzo VPN muammosi",
                    "\n".join(problems),
                    getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    [e.strip() for e in alert_to.split(",") if e.strip()],
                    fail_silently=True,
                )
            except Exception:  # email ishlamasa tekshiruv natijasi baribir logda qoladi
                pass
        raise SystemExit(1)
