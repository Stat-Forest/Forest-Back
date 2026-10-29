"""Excel import yordamchilari — `services/imports.py` dan (buyruqlar va API bitta manba)."""
from django.core.management.base import CommandError

from apps.yashil.services.imports import (  # noqa: F401 — eski import yo'llari uchun
    FALSE_WORDS,
    TRUE_WORDS,
    ImportFileError,
    ImportResult,
    Sheet,
    norm_header,
    parse_bool,
    parse_date,
    read_sheet,
    text,
)


def run_import(command, func, *args, **kwargs):
    """Servis importini buyruqdan chaqiradi: fayl xatosi — CommandError, natija — stdout."""
    try:
        result = func(*args, **kwargs)
    except ImportFileError as exc:
        raise CommandError(str(exc))
    for line in result.lines():
        command.stdout.write(line)
    return result
