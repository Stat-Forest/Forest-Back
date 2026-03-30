from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import KnowledgeDocument, KnowledgeChunk
from ..base.admin import admin_site


@admin.register(KnowledgeDocument, site=admin_site)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_type", "is_active", "created_at", "view_chunks_link")
    list_filter = ("source_type", "is_active")
    search_fields = ("title", "content")
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('title', 'source_type', 'content')
        }),
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('source_key', 'metadata'),
            'classes': ('collapse',)
        }),
        ("Holati", {
            'fields': ('is_active',)
        }),
        ("Vaqt ma'lumotlari", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def view_chunks_link(self, obj):
        count = obj.chunks.count()
        url = reverse('admin:ai_knowledgechunk_changelist') + f'?document__id={obj.id}'
        return format_html('<a href="{}"><i class="fas fa-link"></i> {} ta chunk</a>', url, count)

    view_chunks_link.short_description = "Chunklar"
    view_chunks_link.allow_tags = True


@admin.register(KnowledgeChunk, site=admin_site)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document_link", "chunk_index", "token_count", "created_at")
    list_filter = ("created_at", "document__source_type")
    search_fields = ("text", "document__title")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('document', 'chunk_index', 'text')
        }),
        ("Texnik ma'lumotlar", {
            'fields': ('token_count', 'embedding', 'metadata'),
            'classes': ('collapse',)
        }),
        ("Vaqt ma'lumotlari", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def document_link(self, obj):
        url = reverse('admin:ai_knowledgedocument_change', args=[obj.document.id])
        return format_html('<a href="{}">{}</a>', url, obj.document.title)

    document_link.short_description = "Hujjat"
    document_link.admin_order_field = "document__title"
