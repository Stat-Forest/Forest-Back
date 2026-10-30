"""OpenAPI tavsifi (TZ §19.1, §21): modulning barcha amallari sxemada to'liq va xatosiz."""
import re

from django.test import SimpleTestCase

from apps.yashil.openapi import build_schema

CYRILLIC = re.compile(r"[А-Яа-яЎўҚқҒғҲҳЁё]")
METHODS = ("get", "post", "put", "patch", "delete")


def _operations(schema):
    for path, item in schema["paths"].items():
        for method in METHODS:
            if method in item:
                yield path, method, item[method]


class YashilOpenApiTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema, cls.problems = build_schema(collect_problems=True)

    def test_no_generator_errors_or_warnings(self):
        self.assertEqual(self.problems, [])

    def test_all_module_urls_documented(self):
        from django.urls import URLPattern

        from apps.yashil import urls

        documented = set(self.schema["paths"])
        self.assertEqual(len(documented), len([p for p in urls.urlpatterns if isinstance(p, URLPattern)]))
        self.assertTrue(all(p.startswith("/api/v1/yashil/") for p in documented))

    def test_every_operation_has_cyrillic_summary_and_tag(self):
        for path, method, op in _operations(self.schema):
            with self.subTest(path=path, method=method):
                self.assertRegex(op.get("summary", ""), CYRILLIC)
                self.assertTrue(op.get("tags"))

    def test_operation_ids_unique(self):
        ids = [op["operationId"] for _, _, op in _operations(self.schema)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_idempotent_posts_require_key(self):
        op = self.schema["paths"]["/api/v1/yashil/orders/{order_id}/submit/"]["post"]
        header = next(p for p in op["parameters"] if p["name"] == "Idempotency-Key")
        self.assertEqual(header["in"], "header")
        self.assertTrue(header["required"])
        plain = self.schema["paths"]["/api/v1/yashil/orders/"]["post"]
        self.assertNotIn("Idempotency-Key", [p["name"] for p in plain.get("parameters", [])])

    def test_cabinet_header_and_error_contract(self):
        op = self.schema["paths"]["/api/v1/yashil/orders/{order_id}/accept/"]["post"]
        self.assertIn("X-Yashil-Cabinet", [p["name"] for p in op["parameters"]])
        for code in ("401", "403", "404", "409", "422"):
            self.assertIn(code, op["responses"])
        ref = op["responses"]["422"]["content"]["application/json"]["schema"]["$ref"]
        self.assertTrue(ref.endswith("/YashilError"))
        error = self.schema["components"]["schemas"]["YashilError"]["properties"]
        for field in ("error_code", "field", "message", "request_id"):
            self.assertIn(field, error)

    def test_public_verify_has_no_auth(self):
        op = self.schema["paths"]["/api/v1/yashil/verify/{token}/"]["get"]
        self.assertEqual(op.get("security"), [{}])
        self.assertNotIn("X-Yashil-Cabinet", [p["name"] for p in op.get("parameters", [])])

    def test_request_bodies_use_module_serializers(self):
        body = self.schema["paths"]["/api/v1/yashil/orders/"]["post"]["requestBody"]
        self.assertTrue(body["content"]["application/json"]["schema"]["$ref"].endswith("/OrderWriteRequest"))
        listing = self.schema["paths"]["/api/v1/yashil/orders/"]["get"]["responses"]["200"]
        props = self.schema["components"]["schemas"][listing["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[1]]["properties"]
        self.assertIn("results", props)
        self.assertIn("count", props)
