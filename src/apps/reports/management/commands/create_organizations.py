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
                ("O'rmon agentligi", "Лесное агентство", 200934675),
                ("O'rmon xo'jaligini raqamlashtirish markazi davlat muassasasi",
                 'Государственное учреждение "Центр цифровизации лесного хозяйства"', 305638965),
                ("YASHIL HUDUD unitar korxonasi", 'Унитарное предприятие "ЯШИЛ ХУДУД"', 309519778),
                ("O'rmonqurilish davlat unitar korxonasi", 'Государственное унитарное предприятие "Урмонкурилиш"',
                 305638958),
                ("Qoraqalpog'iston Respublikasi O'rmon xo'jaligi agentligi",
                 "Агентство лесного хозяйства Республики Каракалпакстан", 201443280),
                ("Dorivor o'simliklarni yetishtirish va qayta ishlash ilmiy-ishlab chiqarish markazi",
                 "Научно-производственный центр по выращиванию и переработке лекарственных растений", 200917434),
            ],
            RegionChoices.QORAQALPAQSTAN: [
                ("Bo'zatov davlat o'rmon xo'jaligi", "Бозатауское государственное лесное хозяйство", 200380457),
                ("Mo'ynoq davlat o'rmon xo'jaligi", "Муйнакское государственное лесное хозяйство", 200387344),
                ("Xo'jayli davlat o'rmon xo'jaligi", "Ходжейлийское государственное лесное хозяйство", 201029035),
                ("Nukus davlat o'rmon xo'jaligi", "Нукусское государственное лесное хозяйство", 200388105),
                ("Taxtako'pir davlat o'rmon xo'jaligi", "Тахтакупырское государственное лесное хозяйство", 200390025),
                ("Beruniy davlat o'rmon xo'jaligi", "Берунийское государственное лесное хозяйство", 201604293),
                ("Qipchoq davlat o'rmon xo'jaligi", "Кипчакское государственное лесное хозяйство", 200374029),
                ("Ellikqal'a davlat o'rmon xo'jaligi", "Элликкалинское государственное лесное хозяйство", 200401294),
                ("Chimboy davlat o'rmon xo'jaligi", "Чимбайское государственное лесное хозяйство", 200397584),
                ("To'rtko'l davlat o'rmon xo'jaligi", "Турткульское государственное лесное хозяйство", 200392125),
                ("Qorao'zak davlat o'rmon xo'jaligi", "Караузякское государственное лесное хозяйство", 200914644),
                ("Nukus maxsus davlat o'rmon xo'jaligi", "Нукусское специальное государственное лесное хозяйство",
                 201008741),
                ("Shumanay ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Шуманайское специализированное государственное лесное хозяйство", 207283588),
                ("Qonliko'l ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Канлыкульское специализированное государственное лесное хозяйство", 207283951),
            ],
            RegionChoices.ANDIJON: [
                ("Andijon davlat o'rmon xo'jaligi", "Андижанское государственное лесное хозяйство", 200240306),
            ],
            RegionChoices.BUXORO: [
                ("Buxoro davlat o'rmon xo'jaligi", "Бухарское государственное лесное хозяйство", 203621880),
                ("G'ijduvon davlat o'rmon xo'jaligi", "Гиждуванское государственное лесное хозяйство", 201073727),
                ("Jondor davlat o'rmon xo'jaligi", "Жондорское государственное лесное хозяйство", 201808102),
                ("Olot davlat o'rmon xo'jaligi", "Алатское государственное лесное хозяйство", 201365814),
                ("Qorako'l davlat o'rmon xo'jaligi", "Каракульское государственное лесное хозяйство", 200881086),
                ("Qizilqum davlat o'rmon xo'jaligi", "Кызылкумское государственное лесное хозяйство", 200976663),
                ("Neftchi davlat o'rmon xo'jaligi", "Нефтяное государственное лесное хозяйство", 202312292),
                ("Shofirkon davlat o'rmon xo'jaligi", "Шафирканское государственное лесное хозяйство", 201114190),
                ("Qorovulbozor davlat o'rmon xo'jaligi", "Караулбазарское государственное лесное хозяйство", 200978881),
                ("Kogon ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Каганское специализированное государственное лесное хозяйство", 308780924),
                ("Qorako'l ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Каракульское специализированное государственное лесное хозяйство", 200878144),
            ],
            RegionChoices.JIZZAX: [
                ("Jizzax davlat o'rmon xo'jaligi", "Джизакское государственное лесное хозяйство", 205413204),
                ("Baxmal davlat o'rmon xo'jaligi", "Бахмальское государственное лесное хозяйство", 201030162),
                ("Zomin davlat o'rmon xo'jaligi", "Зааминское государственное лесное хозяйство", 200335978),
                ("Forish davlat o'rmon xo'jaligi", "Фаришское государственное лесное хозяйство", 200340459),
                ("G'allaorol ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Галляаральское специализированное государственное лесное хозяйство", 207332139),
                ("Xo'jamushkent davlat o'rmon xo'jaligi", "Ходжамушкентское государственное лесное хозяйство",
                 201479426),
            ],
            RegionChoices.QASHQADARYO: [
                ("Qashqadaryo davlat o'rmon xo'jaligi", "Кашкадарьинское государственное лесное хозяйство", 201998643),
                ("Qamashi davlat o'rmon xo'jaligi", "Камашинское государственное лесное хозяйство", 201716748),
                ("Muborak davlat o'rmon xo'jaligi", "Мубарекское государственное лесное хозяйство", 200697780),
                ("Sho'rtan davlat o'rmon xo'jaligi", "Шуртанское государственное лесное хозяйство", 202611055),
                ("Kitob davlat o'rmon xo'jaligi", "Китабское государственное лесное хозяйство", 200694065),
                ("Qumdaryo davlat o'rmon xo'jaligi", "Кумдарьинское государственное лесное хозяйство", 306462806),
                ("Dexqonobod davlat o'rmon xo'jaligi", "Дехканабадское государственное лесное хозяйство", 201047211),
                ("Yakkabog' ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Яккабагское специализированное государственное лесное хозяйство", 200710234),
                ("Jovuz davlat o'rmon xo'jaligi", "Джавузское государственное лесное хозяйство", 200694833),
                ("Shaxrisabz ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Шахрисабзское специализированное государственное лесное хозяйство", 305679227),
            ],
            RegionChoices.NAVOIY: [
                ("Navoiy davlat o'rmon xo'jaligi", "Навоийское государственное лесное хозяйство", 201553120),
                ("Konimex davlat o'rmon xo'jaligi", "Канимехское государственное лесное хозяйство", 200014087),
                ("Xatirchi davlat o'rmon xo'jaligi", "Хатырчинское государственное лесное хозяйство", 200911332),
                ("Uchquduq davlat o'rmon xo'jaligi", "Учкудукское государственное лесное хозяйство", 200011004),
                ("Tomdi davlat o'rmon xo'jaligi", "Тамдынское государственное лесное хозяйство", 200019174),
                ("Nurota davlat o'rmon xo'jaligi", "Нуратинское государственное лесное хозяйство", 305062988),
                ("Navbaxor davlat o'rmon ishlab chiqarish korxonasi",
                 "Навбахорское государственное лесопроизводственное предприятие", 205704166),
            ],
            RegionChoices.NAMANGAN: [
                ("Namangan davlat o'rmon xo'jaligi", "Наманганское государственное лесное хозяйство", 200048875),
                ("Kosonsoy davlat o'rmon xo'jaligi", "Касансайское государственное лесное хозяйство", 200074583),
                ("Pop ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Папское специализированное государственное лесное хозяйство", 200087400),
                ("O'rtaorol davlat o'rmon ishlab chiqarish korxonasi",
                 "Среднеаральское государственное лесопроизводственное предприятие", 205683828),
            ],
            RegionChoices.SAMARQAND: [
                ("Samarqand davlat o'rmon xo'jaligi", "Самаркандское государственное лесное хозяйство", 203427544),
                ("Paxtachi davlat o'rmon xo'jaligi", "Пахтачинское государственное лесное хозяйство", 202402616),
                ("Saroyqo'rg'on davlat o'rmon xo'jaligi", "Сарайкурганское государственное лесное хозяйство",
                 200779780),
                ("Kattaqo'rg'on davlat o'rmon xo'jaligi", "Каттакурганское государственное лесное хозяйство",
                 200747496),
                ("Jomboy davlat o'rmon xo'jaligi", "Джамбайское государственное лесное хозяйство", 201180665),
                ("Oqdaryo davlat o'rmon xo'jaligi", "Акдарьинское государственное лесное хозяйство", 203289510),
                ("Ishtihon davlat o'rmon xo'jaligi", "Иштиханское государственное лесное хозяйство", 308733750),
                ("Urgut ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Ургутское специализированное государственное лесное хозяйство", 308421585),
                ("Fozilmon ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Фазылманское специализированное государственное лесное хозяйство", 305671088),
                ("Darg'om davlat o'rmon ishlab chiqarish korxonasi",
                 "Даргомское государственное лесопроизводственное предприятие", 205671218),
            ],
            RegionChoices.SIRDARYO: [
                ("Sirdaryo davlat o'rmon xo'jaligi", "Сырдарьинское государственное лесное хозяйство", 201166809),
            ],
            RegionChoices.SURXONDARYO: [
                ("Surxondaryo davlat o'rmon xo'jaligi", "Сурхандарьинское государственное лесное хозяйство", 200478261),
                ("Boysun davlat o'rmon xo'jaligi", "Байсунское государственное лесное хозяйство", 201325009),
                ("Qiziriq davlat o'rmon xo'jaligi", "Кизирикское государственное лесное хозяйство", 203662585),
                ("Uzun davlat o'rmon xo'jaligi", "Длинное государственное лесное хозяйство", 201467250),
                ("Bobotog' davlat o'rmon xo'jaligi", "Боботогское государственное лесное хозяйство", 204426394),
                ("\"Xisor\" ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Специализированное государственное лесное хозяйство \"Гиссар\"", 200493846),
            ],
            RegionChoices.TASHKENT: [
                ("Toshkent davlat o'rmon xo'jaligi", "Ташкентское государственное лесное хозяйство", 200663214),
                ("Bekobod davlat o'rmon xo'jaligi", "Бекабадское государственное лесное хозяйство", 200556283),
                ("Burchmulla davlat o'rmon xo'jaligi", "Бурчмуллинское государственное лесное хозяйство", 200438857),
                ("Ohangaron davlat o'rmon xo'jaligi", "Ахангаранское государственное лесное хозяйство", 200608534),
                ("Saksonota davlat o'rmon ishlab chiqarish korxonasi",
                 "Саксанотинское государственное лесопроизводственное предприятие", 205693166),
                ("Quyichirchiq ixtisoslashgan davlat o'rmon xo'jaligi",
                 "Куйичирчикское специализированное государственное лесное хозяйство", 200458033),
            ],
            RegionChoices.FARGONA: [
                ("Farg'ona davlat o'rmon xo'jaligi", "Ферганское государственное лесное хозяйство", 200145494),
                ("Qo'qon davlat o'rmon xo'jaligi", "Кокандское государственное лесное хозяйство", 200127570),
            ],
            RegionChoices.XORAZM: [
                ("Xorazm davlat o'rmon xo'jaligi", "Хорезмское государственное лесное хозяйство", 200408996),
            ],
        }

        organizations = []
        for region, orgs in org_data.items():
            for name_uz, name_ru, stir in orgs:
                organizations.append(
                    Organization(
                        name=name_uz,
                        name_uz=name_uz,
                        name_ru=name_ru,
                        stir=stir,
                        region=region
                    )
                )

        Organization.objects.bulk_create(organizations)
        self.stdout.write(self.style.SUCCESS(f"{len(organizations)} organizations created successfully."))