def get_translated_choices(choices_class):
    return [
        {"key": choice.value, "label": str(choice.label)} for choice in choices_class
    ]
