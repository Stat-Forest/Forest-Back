"""Hujjat shablonlari uchun matn: `{% d "Рақами" %}`, `{% d "Жой: {0}" c.place %}` — hujjat tili `c.lang` dan."""
from django import template

from apps.yashil.services.lang import doc_text

register = template.Library()


@register.simple_tag(takes_context=True)
def d(context, text, *values):
    content = context.get("c") or {}
    return doc_text(text, content.get("lang"), *values)
