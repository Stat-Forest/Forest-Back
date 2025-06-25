def get_translated_field(obj, field, lang, default_lang="uz"):
    if not obj:
        return ""

    field_lang = f"{field}_{lang}"
    default_field = f"{field}_{default_lang}"

    return (
        getattr(obj, field_lang, None)
        or getattr(obj, default_field, None)
        or getattr(obj, field, "")
    )
