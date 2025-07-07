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
                ("O‘rmonqurilish davlat unitar korxonasi", "Государственное унитарное предприятие Лесострой"),
                ("O‘rmontexnoservis davlat unitar korxonasi", "ГУП Лестехносервис"),
                ("Dorivor o‘simliklarni yetishtirish va qayta ishlash markazi",
                 "Центр выращивания и переработки лекарственных растений"),
                ("O‘rmon xo‘jaligi texnikumi", "Техникум лесного хозяйства"),
            ],
            RegionChoices.OTHERS: [
                ("O‘rmon xo‘jaligi ilmiy-tadqiqot instituti (Andijon)", "НИИ лесного хозяйства (Андижан)"),
                ("O‘rmon xo‘jaligini rivojlantirish innovatsion markazi",
                 "Инновационный центр развития лесного хозяйства"),
                ("Cho‘l hududlarida o‘rmonchilikni rivojlantirish markazi",
                 "Центр развития лесного хозяйства в пустынных регионах"),
                ("Chorvoq suv ombori atrofini obodonlashtirish direksiyasi",
                 "Дирекция по благоустройству Чарвакского водохранилища"),
            ],
            RegionChoices.QORAQALPAQSTAN: [
                ("Orolbo‘yi Mintaqaviy texnika bazasi", "Региональная техническая база Приаралья"),
                ("Beruniy DUK", "Беруни ГУП"),
                ("Bo‘zatov DUK", "Бузатов ГУП"),
                ("Qipchoq DUK", "Кипчак ГУП"),
                ("Qozoqdaryo DO‘X", "Казахдарья ЛХУ"),
                ("Qonliko‘l IDUK", "Канлыкуль ИГУП"),
                ("Qorauzak DUK", "Караузяк ГУП"),
                ("Qo‘ng‘irot DO‘X", "Кунград ЛХУ"),
                ("Mo‘ynoq DUK", "Муйнак ГУП"),
                ("Nukus DUK", "Нукус ГУП"),
                ("Nukus maxsus DUK", "Нукус спец. ГУП"),
                ("Taxtako‘pir DUK", "Тахтакупыр ГУП"),
                ("To‘rtko‘l DUK", "Турткуль ГУП"),
                ("Xo‘jayli DUK", "Ходжейли ГУП"),
                ("Chimboy DUK", "Чимбай ГУП"),
                ("Shumanay IDUK", "Шуманай ИГУП"),
                ("Ellikqala DUK", "Элликкала ГУП"),
                ("Orolqum Mintaqaviy texnika bazasi", "Региональная техническая база Оролкум"),
            ],
            RegionChoices.ANDIJON: [
                ("Andijon DUK", "Андижан ГУП"),
            ],
            RegionChoices.BUXORO: [
                ("Neftchi DUK", "Нефтчи ГУП"),
                ("Buxoro DUK", "Бухара ГУП"),
                ("Buxoro ITS", "Бухара ИТС"),
                ("G‘ijduvon DUK", "Гиждуван ГУП"),
                ("Jondor DUK", "Жондор ГУП"),
                ("Kogon IDUK", "Когон ИГУП"),
                ("Qizilqum DUK", "Кызылкум ГУП"),
                ("Qorako‘l DUK", "Каракуль ГУП"),
                ("Qorako‘l DO‘X", "Каракуль ЛХУ"),
                ("Qorako‘l IDUK", "Каракуль ИГУП"),
                ("Qorovulbozor DUK", "Каравулбазар ГУП"),
                ("Qorovulbozor DO‘X", "Каравулбазар ЛХУ"),
                ("Olot DUK", "Алат ГУП"),
                ("Shofirkon DUK", "Шафиркан ГУП"),
            ],
            RegionChoices.JIZZAX: [
                ("Baxmal DUK", "Бахмал ГУП"),
                ("G‘allaorol IDUK", "Галляарал ИГУП"),
                ("Jizzax DUK", "Джизак ГУП"),
                ("Zomin DUK", "Зомин ГУП"),
                ("Pistachilik ITS", "Фисташковый ИТС"),
                ("Zomin Mintaqaviy texnika bazasi", "Зоминская региональная техническая база"),
                ("Forish DUK", "Фориш ГУП"),
                ("Forish DO‘X", "Фориш ЛХУ"),
                ("Xo‘jamushkent DUK", "Хужамушкент ГУП"),
            ],
            RegionChoices.QASHQADARYO: [
                ("Dehqonobod DUK", "Дехканабад ГУП"),
                ("Jovuz DUK", "Джовуз ГУП"),
                ("Kitob DUK", "Китаб ГУП"),
                ("Qamashi DUK", "Камаши ГУП"),
                ("Qashqadaryo DUK", "Кашкадарья ГУП"),
                ("Qumdarё DUK", "Кумдарья ГУП"),
                ("Muborak DUK", "Муборак ГУП"),
                ("Muborak DO‘X", "Муборак ЛХУ"),
                ("Shahrisabz IDUK", "Шахрисабз ИГУП"),
                ("Sho‘rtan DUK", "Шуртан ГУП"),
                ("Yakkabog‘ IDUK", "Яккабаг ИГУП"),
            ],
            RegionChoices.NAVOIY: [
                ("Konimeh DUK", "Канимех ГУП"),
                ("Navbahor DO‘ICHK", "Навбахор ДОИЧК"),
                ("Navoiy DUK", "Навои ГУП"),
                ("Nurota DUK", "Нурата ГУП"),
                ("Nurota DO‘X", "Нурата ЛХУ"),
                ("Tomdi DUK", "Томди ГУП"),
                ("Uchquduq DUK", "Учкудук ГУП"),
                ("Xatirchi DUK", "Хатырчи ГУП"),
            ],
            RegionChoices.NAMANGAN: [
                ("Kosonsoy DUK", "Касансай ГУП"),
                ("Namangan DUK", "Наманган ГУП"),
                ("Pop IDUK", "Пап ИГУП"),
                ("O‘rtaorol DO‘ICHQ", "Уртаорол ДОИЧК"),
                ("Pop Mintaqaviy texnika bazasi", "Папская региональная техническая база"),
            ],
            RegionChoices.SAMARQAND: [
                ("Darg‘om DO‘ICHQ", "Даргом ДОИЧК"),
                ("Jomboy DUK", "Жамбай ГУП"),
                ("Zarafshon Mintaqaviy texnika bazasi", "Зарафшанская региональная техническая база"),
                ("Ishtixon DUK", "Иштихан ГУП"),
                ("Kattaqo‘rg‘on DUK", "Каттакурган ГУП"),
                ("Oqdaryo DUK", "Акдарья ГУП"),
                ("Paxtachi DUK", "Пахтачи ГУП"),
                ("Samarqand DUK", "Самарканд ГУП"),
                ("Saroyqo‘rg‘on DUK", "Сарайкурган ГУП"),
                ("Urgut IDUK", "Ургут ИГУП"),
                ("Fozilmon IDUK", "Фазилмон ИГУП"),
                ("Omonqo‘ton Mintaqaviy texnika bazasi", "Региональная техническая база Омонкутон"),
            ],
            RegionChoices.SIRDARYO: [
                ("Qolgansir DO‘X", "Калгансир ЛХУ"),
                ("Sirdaryo DUK", "Сырдарья ГУП"),
            ],
            RegionChoices.SURXONDARYO: [
                ("Bobotog‘ DUK", "Боботаг ГУП"),
                ("Boysun DUK", "Байсун ГУП"),
                ("Qiziriq DUK", "Кизирик ГУП"),
                ("Surxondaryo DUK", "Сурхандарья ГУП"),
                ("Uzun DUK", "Узун ГУП"),
                ("Hisor IDUK", "Хисор ИГУП"),
                ("Bobotog‘ Mintaqaviy texnika bazasi", "Региональная техническая база Боботаг"),
                ("Yuqori To‘palang Mintaqaviy texnika bazasi", "Региональная техническая база Юкори Тупаланг"),
            ],
            RegionChoices.TASHKENT: [
                ("Bekobod DUK", "Бекабад ГУП"),
                ("Burchmulla DUK", "Бурчмула ГУП"),
                ("Dalvarzin DO‘X", "Далварзин ЛХУ"),
                ("Darkhon ITS", "Дархан ИТС"),
                ("Quyichirchiq IDUK", "Куйичирчик ИГУП"),
                ("Ohangaron DUK", "Ахангаран ГУП"),
                ("Saksonota DO‘ICHQ", "Саксоната ДОИЧК"),
                ("Toshkent DUK", "Ташкент ГУП"),
                ("Ugom-Chotqol Mintaqaviy texnika bazasi", "Региональная техническая база Угам-Чаткал"),
            ],
            RegionChoices.FARGONA: [
                ("Qo‘qon DUK", "Коканд ГУП"),
                ("Qo‘qon ITS", "Коканд ИТС"),
                ("Farg‘ona DUK", "Фергана ГУП"),
            ],
            RegionChoices.XORAZM: [
                ("Xorazm DUK", "Хорезм ГУП"),
                ("Xorazm DO‘X", "Хорезм ЛХУ"),
                ("Qoraqum ITS", "Каракум ИТС"),
            ],
        }

        organizations = []
        for region, orgs in org_data.items():
            for name_uz, name_ru in orgs:
                organizations.append(
                    Organization(name=name_uz, name_ru=name_ru, region=region)
                )

        Organization.objects.bulk_create(organizations)
        self.stdout.write(self.style.SUCCESS(f"{len(organizations)} organizations created successfully."))