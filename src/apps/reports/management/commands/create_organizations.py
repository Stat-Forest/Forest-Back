from django.core.management import BaseCommand

from apps.general.models import Organization
from apps.utils.services import RegionChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        if Organization.objects.exists():
            self.stdout.write(self.style.ERROR("Organizations already exist!"))
            return

        org_data = {
            RegionChoices.REPUBLIC: [
                "O‘rmonqurilish davlat unitar korxonasi",
                "O‘rmontexnoservis davlat unitar korxonasi",
                "Dorivor o‘simliklarni yetishtirish va qayta ishlash markazi",
                "O‘rmon xo‘jaligi texnikumi",
            ],
            RegionChoices.OTHERS: [
                "O‘rmon xo‘jaligi ilmiy-tadqiqot instituti (Andijon)",
                "O‘rmon xo‘jaligini rivojlantirish innovatsion markazi",
                "Cho‘l hududlarida o‘rmonchilikni rivojlantirish markazi",
                "Chorvoq suv ombori atrofini obodonlashtirish direksiyasi",
            ],
            RegionChoices.QORAQALPAQSTAN: [
                "Orolbo‘yi Mintaqaviy texnika bazasi",
                "Beruniy DUK",
                "Bo‘zatov DUK",
                "Qipchoq DUK",
                "Qozoqdaryo DO‘X",
                "Qonliko‘l IDUK",
                "Qorauzak DUK",
                "Qo‘ng‘irot DO‘X",
                "Mo‘ynoq DUK",
                "Nukus DUK",
                "Nukus maxsus DUK",
                "Taxtako‘pir DUK",
                "To‘rtko‘l DUK",
                "Xo‘jayli DUK",
                "Chimboy DUK",
                "Shumanay IDUK",
                "Ellikqala DUK",
                "Orolqum Mintaqaviy texnika bazasi",
            ],
            RegionChoices.ANDIJON: ["Andijon DUK"],
            RegionChoices.BUXORO: [
                "Neftchi DUK",
                "Buxoro DUK",
                "Buxoro ITS",
                "G‘ijduvon DUK",
                "Jondor DUK",
                "Kogon IDUK",
                "Qizilqum DUK",
                "Qorako‘l DUK",
                "Qorako‘l DO‘X",
                "Qorako‘l IDUK",
                "Qorovulbozor DUK",
                "Qorovulbozor DO‘X",
                "Olot DUK",
                "Shofirkon DUK",
            ],
            RegionChoices.JIZZAX: [
                "Baxmal DUK",
                "G‘allaorol IDUK",
                "Jizzax DUK",
                "Zomin DUK",
                "Pistachilik ITS",
                "Zomin Mintaqaviy texnika bazasi",
                "Forish DUK",
                "Forish DO‘X",
                "Xo‘jamushkent DUK",
            ],
            RegionChoices.QASHQADARYO: [
                "Dehqonobod DUK",
                "Jovuz DUK",
                "Kitob DUK",
                "Qamashi DUK",
                "Qashqadaryo DUK",
                "Qumdarё DUK",
                "Muborak DUK",
                "Muborak DO‘X",
                "Shahrisabz IDUK",
                "Sho‘rtan DUK",
                "Yakkabog‘ IDUK",
            ],
            RegionChoices.NAVOIY: [
                "Konimeh DUK",
                "Navbahor DO‘ICHK",
                "Navoiy DUK",
                "Nurota DUK",
                "Nurota DO‘X",
                "Tomdi DUK",
                "Uchquduq DUK",
                "Xatirchi DUK",
            ],
            RegionChoices.NAMANGAN: [
                "Kosonsoy DUK",
                "Namangan DUK",
                "Pop IDUK",
                "O‘rtaorol DO‘ICHQ",
                "Pop Mintaqaviy texnika bazasi",
            ],
            RegionChoices.SAMARQAND: [
                "Darg‘om DO‘ICHQ",
                "Jomboy DUK",
                "Zarafshon Mintaqaviy texnika bazasi",
                "Ishtixon DUK",
                "Kattaqo‘rg‘on DUK",
                "Oqdaryo DUK",
                "Paxtachi DUK",
                "Samarqand DUK",
                "Saroyqo‘rg‘on DUK",
                "Urgut IDUK",
                "Fozilmon IDUK",
                "Omonqo‘ton Mintaqaviy texnika bazasi",
            ],
            RegionChoices.SIRDARYO: [
                "Qolgansir DO‘X",
                "Sirdaryo DUK",
            ],
            RegionChoices.SURXONDARYO: [
                "Bobotog‘ DUK",
                "Boysun DUK",
                "Qiziriq DUK",
                "Surxondaryo DUK",
                "Uzun DUK",
                "Hisor IDUK",
                "Bobotog‘ Mintaqaviy texnika bazasi",
                "Yuqori To‘palang Mintaqaviy texnika bazasi",
            ],
            RegionChoices.TASHKENT: [
                "Bekobod DUK",
                "Burchmulla DUK",
                "Dalvarzin DO‘X",
                "Darkhon ITS",
                "Quyichirchiq IDUK",
                "Ohangaron DUK",
                "Saksonota DO‘ICHQ",
                "Toshkent DUK",
                "Ugom-Chotqol Mintaqaviy texnika bazasi",
            ],
            RegionChoices.FARGONA: [
                "Qo‘qon DUK",
                "Qo‘qon ITS",
                "Farg‘ona DUK",
            ],
            RegionChoices.XORAZM: [
                "Xorazm DUK",
                "Xorazm DO‘X",
                "Qoraqum ITS",
            ],
        }

        organizations = []
        for region, names in org_data.items():
            for name in names:
                organizations.append(Organization(name=name, region=region))

        Organization.objects.bulk_create(organizations)
        self.stdout.write(self.style.SUCCESS(f"{len(organizations)} organizations created successfully."))