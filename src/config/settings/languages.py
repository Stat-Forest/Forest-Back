from django.conf import settings


LANGUAGE_CODE = 'uz'

LANGUAGES = [
    ('uz', 'Uzbek (Latin)'),
    ('uz-cyrl', 'Uzbek (Cyrillic)'),
    ('ru', 'Russian'),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = 'uz'
MODELTRANSLATION_PREPOPULATE_LANGUAGE = 'uz'
MODELTRANSLATION_LANGUAGE = ('uz', 'uz-cyrl', 'ru')

USE_I18N = True

LOCALE_PATHS = [
    settings.BASE_DIR / 'locale',
]
