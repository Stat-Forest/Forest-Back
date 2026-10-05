from django.contrib import admin

from apps.reports.models import ReportSignature


@admin.register(ReportSignature)
class ReportSignatureAdmin(admin.ModelAdmin):
    """Imzolar faqat o'qish uchun: ular API orqali yaratiladi va o'zgartirilmaydi."""
    list_display = ("report", "quarter", "signer_cn", "signer_tin", "signed_at", "is_valid", "verify_status")
    list_filter = ("is_valid", "verify_status", "quarter")
    search_fields = ("signer_cn", "signer_tin", "signer_pinfl", "report__organization__name", "document_hash")
    ordering = ("-created_at",)
    readonly_fields = [
        "report", "quarter", "signer", "signer_cn", "signer_tin", "signer_pinfl",
        "cert_serial", "cert_valid_from", "cert_valid_to", "signed_at",
        "document", "document_hash", "items_hash", "pkcs7", "verify_status",
        "verify_result", "is_valid", "created_at", "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
