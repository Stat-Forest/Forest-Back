import os

# Celery konfiguratsiyasi
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redist_data:6379/0')  # Broker URL (masalan Redis)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redist_data:6379/0')  # Natija saqlash joyi (Redis)
CELERY_TASK_SERIALIZER = os.getenv('CELERY_TASK_SERIALIZER', 'json')  # Vazifalarni serializatsiya qilish format
CELERY_RESULT_SERIALIZER = os.getenv('CELERY_RESULT_SERIALIZER', 'json')  # Natijalarni serializatsiya qilish format
CELERY_TASK_TRACK_STARTED = os.getenv('CELERY_TASK_TRACK_STARTED', True)  # Vazifa boshlanishini kuzatish
CELERY_TIMEZONE = os.getenv('CELERY_TIMEZONE')  # Vaqt zonasini sozlash
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = os.getenv('CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP', True)  # Brokerga ulanganda qayta urinib ko‘rish