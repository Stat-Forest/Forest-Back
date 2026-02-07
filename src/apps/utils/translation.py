from modeltranslation.utils import build_localized_fieldname

def get_translated_field(obj, field: str, lang: str, default_lang: str = "uz"):
    if not obj:
        return ""

    lang_map = {
        "uz": "uz",
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
    if source is None:
        return default_lang

    if isinstance(source, str):
        return source if source in ["uz", "ru"] else default_lang

    if hasattr(source, "query_params"):
        lang = source.query_params.get("lang")
    elif isinstance(source, dict):
        lang = source.get("lang")
    else:
        lang = None

    if lang and lang.lower() in ["uz", "ru"]:
        return lang.lower()

    return default_lang
