from modeltranslation.utils import build_localized_fieldname

def get_translated_field(obj, field: str, lang: str, default_lang: str = "uz"):
    if not obj:
        return ""

    lang_map = {
        "uz": "uz",
        "uz-cyrl": "uz_cyrl",
        "ru": "ru",
    }

    lang_code = lang_map.get(lang, default_lang)
    default_code = lang_map.get(default_lang, "uz")

    lang_field = build_localized_fieldname(field, lang_code)
    default_field = build_localized_fieldname(field, default_code)

    return (
        getattr(obj, lang_field, None)
        or getattr(obj, default_field, None)
        or getattr(obj, field, "")
    )


def get_lang_code(source, default_lang="uz"):
    """
    Accepts a request object or context dict and returns language code.
    """
    if source is None:
        return default_lang

    if hasattr(source, "query_params"):
        query_lang = source.query_params.get("lang")

    elif isinstance(source, dict):
        query_lang = source.get("lang")

    else:
        query_lang = None

    if query_lang:
        query_lang = query_lang.lower()
        if query_lang in ["uz", "ru", "uz-cyrl"]:
            return query_lang

    if hasattr(source, "META"):
        raw = source.META.get("HTTP_ACCEPT_LANGUAGE", default_lang)
    else:
        raw = default_lang

    lang = raw.split(",")[0].strip().lower()

    if lang.startswith("uz-") and "cyrl" in lang:
        return "uz-cyrl"
    elif lang.startswith("uz"):
        return "uz"
    elif lang.startswith("ru"):
        return "ru"

    return default_lang