import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()
from apps.reports.models import Plant
print([(type(p[0]), type(p[1])) for p in Plant.objects.all().values_list('id', 'name')[:1]])
