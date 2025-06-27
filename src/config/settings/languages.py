from django.conf import settings


LANGUAGE_CODE = 'uz'

LANGUAGES = [
    ('uz', 'Uzbek (Latin)'),
    ('ru', 'Russian'),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = 'uz'
MODELTRANSLATION_PREPOPULATE_LANGUAGE = 'uz'
MODELTRANSLATION_LANGUAGES = ('uz', 'ru')

USE_I18N = True

LOCALE_PATHS = [
    settings.BASE_DIR / 'locale',
]
