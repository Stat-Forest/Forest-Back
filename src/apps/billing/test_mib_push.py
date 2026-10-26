"""MIB Push Service: payload formati, JWT, yuborish, takrorlanmaslik, qayta urinish, buyruq."""
import json
import os
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from unittest import mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user
from apps.billing.models import Contract, LandType, MibPushLog
from apps.billing.services import mib_push

URL = f"{BASE}/contracts/"
POST = "apps.billing.services.mib_push.requests.post"


def _response(status_code=200, body=""):
    resp = mock.Mock(status_code=status_code, text=body)
    resp.json.side_effect = lambda: json.loads(body)
    return resp


class MibPushTestBase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key_dir = tempfile.mkdtemp()
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key_path = os.path.join(cls.key_dir, "private.pem")
        with open(cls.key_path, "wb") as fh:
            fh.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        cls.public_key = key.public_key()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.key_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.mib = {**settings.MIB_PUSH, "ENABLED": True, "PRIVATE_KEY_PATH": self.key_path,
                    "BASE_URL": "https://push.example", "SYSTEM_NAME": "billing-urmon", "SUBSCRIBERS": ["tashqi_manbaa_at"]}
        override = override_settings(MIB_PUSH=self.mib)
        override.enable()
        self.addCleanup(override.disable)
        self.ref = make_reference(inn="201234567")
        self.user = make_user("billing", "billing_super")
        self.client = auth(self.client, self.user)

    def create(self, **overrides):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(URL, contract_payload(self.ref, **overrides), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        return Contract.objects.get(id=resp.data["id"])


class PayloadTest(MibPushTestBase):
    def test_payload_matches_legacy_format(self):
        parent = LandType.objects.create(name="O'rmon fondi")
        self.ref.land_type.parent = parent
        self.ref.land_type.save()
        with mock.patch(POST, return_value=_response()):
            contract = self.create(cadastral_number="10:01:02", auction_date="05.01.2026", expired_date="10.01.2031")

        payload = mib_push.build_payload(mib_push.contract_queryset().get(id=contract.id))
        self.assertEqual(payload["department_inn"], "201234567")
        self.assertEqual(payload["department_name"], self.ref.xojalik.name)
        self.assertEqual(payload["cadastral_number"], "10:01:02")
        self.assertEqual(payload["auction_date"], "2026-01-05")
        self.assertEqual(payload["contract_date"], "2026-01-10")
        self.assertEqual(payload["expired_date"], "2031-01-10")
        self.assertEqual(payload["rental_period"], "5 yil")
        self.assertEqual(payload["contract_number"], "SH-1")
        self.assertEqual(payload["rent_user_type"], "Jismoniy")
        self.assertEqual(payload["rent_user_inn"], "12345678901234")
        self.assertEqual(payload["rent_user_full_name"], "Test Renter")
        self.assertEqual(payload["rent_user_address"], "Andijon")
        self.assertEqual(payload["rent_user_phone"], "+998901112233")
        self.assertEqual(payload["region_code"], self.ref.region.code)
        self.assertEqual(payload["district_code"], self.ref.district.code)
        self.assertEqual(payload["branch_name"], "Markaziy")
        self.assertEqual(payload["rent_area"], "12.50")
        self.assertEqual(payload["lands"], {f"O'rmon fondi / {self.ref.land_type.name}": "5.00"})
        self.assertEqual(payload["activities"], {self.ref.activity_type.name: "7.50"})
        self.assertEqual(payload["privileges"], {self.ref.privilege_type.name: "1.00"})
        self.assertEqual(payload["rent_amount"], "1100.00")  # yillik hisoblangan summalar yig'indisi
        self.assertIsNone(payload["canceled_date"])
        self.assertIsNone(payload["cancellation_reason"])
        self.assertEqual(set(payload), {
            "department_inn", "department_name", "cadastral_number", "auction_date", "contract_date", "expired_date",
            "rental_period", "contract_number", "rent_user_type", "rent_user_inn", "rent_user_full_name",
            "rent_user_address", "rent_user_passport", "rent_user_phone", "region_name", "region_code",
            "district_name", "district_code", "rent_area", "branch_name", "circle_number", "section_number",
            "counter_number", "massive_number", "activities", "lands", "privileges", "rent_amount",
            "canceled_date", "cancellation_reason",
        })


class PushFlowTest(MibPushTestBase):
    def test_create_pushes_with_signed_token(self):
        with mock.patch(POST, return_value=_response(200, '{"ok": true}')) as post:
            contract = self.create()

        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "https://push.example/v3/app/mq/receive")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["destinationSubscribers"], ["tashqi_manbaa_at"])
        self.assertEqual(body["data"]["contract_number"], "SH-1")
        self.assertEqual(body["dtl"], (timezone.localdate() + timedelta(days=self.mib["DTL_DAYS"])).isoformat())
        token = post.call_args.kwargs["headers"]["Authorization"].removeprefix("Bearer ")
        claims = jwt.decode(token, self.public_key, algorithms=["RS512"])
        self.assertEqual(claims["sub"], "billing-urmon")

        log = MibPushLog.objects.get()
        self.assertEqual(str(log.correlation_id), body["correlationId"])
        self.assertEqual(log.contract, contract)
        self.assertEqual(log.status, MibPushLog.Status.SENT)
        self.assertEqual(log.attempts, 1)
        self.assertEqual(log.response, {"ok": True})

    def test_disabled_does_nothing(self):
        self.mib["ENABLED"] = False
        with mock.patch(POST) as post:
            self.create()
        post.assert_not_called()
        self.assertFalse(MibPushLog.objects.exists())

    def test_unchanged_contract_not_resent_but_status_change_is(self):
        with mock.patch(POST, return_value=_response()) as post:
            contract = self.create()
            self.assertIsNone(mib_push.push_contract(contract.id))
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(f"{URL}{contract.id}/status/", {"status": "inactive", "cancel_reason": "Muddatidan oldin"}, format="json")
            self.assertEqual(resp.status_code, 200, resp.data)

        self.assertEqual(post.call_count, 2)
        data = post.call_args.kwargs["json"]["data"]
        self.assertEqual(data["cancellation_reason"], "Muddatidan oldin")
        self.assertEqual(data["canceled_date"], timezone.localdate().isoformat())

    def test_update_pushes_new_state(self):
        with mock.patch(POST, return_value=_response()) as post:
            contract = self.create()
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.patch(f"{URL}{contract.id}/", {"contract": {"cadastral_number": "99:99"}}, format="json")
            self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args.kwargs["json"]["data"]["cadastral_number"], "99:99")

    def test_validation_error_does_not_push(self):
        payload = contract_payload(self.ref)
        payload["lands"] = [{"type": "Mavjud bo'lmagan tur", "area": "1"}]
        with mock.patch(POST) as post, self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        post.assert_not_called()

    def test_broker_failure_does_not_break_request(self):
        with mock.patch("apps.billing.tasks.push_contract_to_mib.delay", side_effect=ConnectionError("redis yo'q")):
            contract = self.create()
        self.assertTrue(Contract.objects.filter(id=contract.id).exists())


class FailureAndRetryTest(MibPushTestBase):
    def test_missing_key_fails_then_retry_sends(self):
        self.mib["PRIVATE_KEY_PATH"] = "/nonexistent/private.pem"
        with mock.patch(POST) as post:
            self.create()
        post.assert_not_called()
        log = MibPushLog.objects.get()
        self.assertEqual(log.status, MibPushLog.Status.FAILED)
        self.assertIn("FileNotFoundError", log.error)

        self.mib["PRIVATE_KEY_PATH"] = self.key_path
        with mock.patch(POST, return_value=_response(204)):
            self.assertEqual(mib_push.retry_failed(), 1)
        log.refresh_from_db()
        self.assertEqual(log.status, MibPushLog.Status.SENT)
        self.assertEqual(log.attempts, 2)

    def test_http_error_and_expiry(self):
        with mock.patch(POST, return_value=_response(500, "<html>500</html>")):
            self.create()
        log = MibPushLog.objects.get()
        self.assertEqual(log.status, MibPushLog.Status.FAILED)
        self.assertEqual(log.http_status, 500)
        self.assertEqual(log.response, {"text": "<html>500</html>"})

        MibPushLog.objects.filter(id=log.id).update(dtl=timezone.localdate() - timedelta(days=1))
        with mock.patch(POST) as post:
            self.assertEqual(mib_push.retry_failed(), 0)
        post.assert_not_called()
        log.refresh_from_db()
        self.assertEqual(log.status, MibPushLog.Status.EXPIRED)

    def test_retry_stops_after_max_attempts(self):
        self.mib["MAX_ATTEMPTS"] = 2
        with mock.patch(POST, return_value=_response(500, "x")) as post:
            self.create()
            mib_push.retry_failed()
            mib_push.retry_failed()
        self.assertEqual(post.call_count, 2)
        self.assertEqual(MibPushLog.objects.get().attempts, 2)

    def test_new_change_supersedes_failed_log(self):
        with mock.patch(POST, return_value=_response(500, "x")):
            contract = self.create()
        with mock.patch(POST, return_value=_response()):
            mib_push.push_contract(contract.id, force=True)
        self.assertEqual(
            sorted(MibPushLog.objects.values_list("status", flat=True)),
            [MibPushLog.Status.EXPIRED, MibPushLog.Status.SENT],
        )


class CommandTest(MibPushTestBase):
    def setUp(self):
        super().setUp()
        self.mib["ENABLED"] = False  # buyruq avtomatik yuborishdan qat'i nazar ishlaydi
        self.old = self.create(contract_number="SH-OLD", pinfl="12345678901111")
        Contract.objects.filter(id=self.old.id).update(updated_at=timezone.now() - timedelta(days=90))
        self.new = self.create(contract_number="SH-NEW", pinfl="12345678902222")

    def run_cmd(self, *args):
        out = StringIO()
        call_command("mib_push", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_dry_run_by_default(self):
        since = (timezone.localdate() - timedelta(days=30)).isoformat()
        with mock.patch(POST) as post:
            out = self.run_cmd("--since", since)
        self.assertIn("Tanlangan shartnomalar: 1", out)
        self.assertIn("DRY-RUN", out)
        post.assert_not_called()

    def test_send_since_and_skip_unchanged(self):
        since = (timezone.localdate() - timedelta(days=30)).isoformat()
        with mock.patch(POST, return_value=_response()) as post:
            self.run_cmd("--since", since, "--send")
            out = self.run_cmd("--all", "--send")
        self.assertEqual(post.call_count, 2)  # SH-NEW, keyin SH-OLD; SH-NEW ikkinchi marta o'tkazildi
        self.assertIn("'skipped': 1", out)
        self.assertEqual(MibPushLog.objects.filter(status=MibPushLog.Status.SENT).count(), 2)

    def test_number_force(self):
        with mock.patch(POST, return_value=_response()) as post:
            self.run_cmd("--number", "SH-OLD", "--send")
            self.run_cmd("--number", "SH-OLD", "--send", "--force")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args.kwargs["json"]["data"]["contract_number"], "SH-OLD")

    def test_requires_selection(self):
        with self.assertRaises(CommandError):
            self.run_cmd("--send")

    def test_check(self):
        self.assertIn("JWT (RS512) yaratildi", self.run_cmd("--check"))
        self.mib["PRIVATE_KEY_PATH"] = "/nonexistent/private.pem"
        with self.assertRaises(CommandError):
            self.run_cmd("--check")
