import random
from django.core.management import BaseCommand

from apps.general.models import Organization
from apps.utils.services import RegionChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        if Organization.objects.all().exists():
            self.stdout.write(self.style.ERROR("Organizations already exist !"))
        else:
            organizations = []
            for _ in range(13):
                org_region = random.choice(RegionChoices.values)
                organizations.append(Organization(
                    name=f'Organization {org_region}',
                    region=org_region
                ))
            Organization.objects.bulk_create(organizations)

        self.stdout.write(self.style.SUCCESS("Organizations have been created !."))