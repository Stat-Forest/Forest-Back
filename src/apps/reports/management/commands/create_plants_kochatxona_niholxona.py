from django.core.management.base import BaseCommand
from modeltranslation.utils import build_localized_fieldname

from apps.reports.models import Plant, Statement

# 🔹 Parent nomlari (tepada chiqadiganlar)
PARENT_NAMES = {
    "Yaproqbarglilar": {"uz": "Yaproqbarglilar", "ru": "Лиственные"},
    "Tez o‘suvchilar": {"uz": "Tez o‘suvchilar", "ru": "Быстрорастущие"},
    "Yong‘oqmevalilar": {"uz": "Yong‘oqmevalilar", "ru": "Орехоплодные"},
    "Mevalilar": {"uz": "Mevalilar", "ru": "Плодовые"},
    "Cho'l o'simliklari": {"uz": "Cho'l o'simliklari", "ru": "Пустынные растения"},
    "Ignabarglilar": {"uz": "Ignabarglilar", "ru": "Хвойные"},
    "Buta va gullar": {"uz": "Butalar va gullar", "ru": "Кустарники и цветы"},
}

# 🔹 Child plantlar
PLANTS_STRUCTURE = {
    "Yaproqbarglilar": [
        ("bagrannik", "багрянник"),
        ("eman chereshch (dub)", "эман черешч (дуб)"),
        ("eman piramid (dub)", "эман пирамид (дуб)"),
        ("qayrogoch (vyaz)", "қайрогоч (вяз)"),
        ("sada qayrog‘och (gujum)", "сада қайроғоч (гужум)"),
        ("shumtol (yasen)", "шумтол (ясень)"),
        ("aylant", "айлант"),
        ("savatol", "саваттол"),
        ("gledichiya", "гледичия"),
        ("chinor", "чинор"),
        ("yapon saforasi", "япон сафораси"),
        ("kashtan", "каштан"),
        ("katalpa", "катальпа"),
        ("xilo katalpa", "хило каталпа"),
        ("oq qayin (beryoza)", "оқ қайин (берёза)"),
        ("zarang (klen)", "заранг (клен)"),
        ("ipak akatsiya", "ипак акация"),
        ("akatsiya", "акация"),
        ("maklyura", "маклюра"),
        ("lipa", "липа"),
        ("qog‘oz daraxt", "қогоз дарахт"),
        ("sovun daraxti", "совун дарахти"),
        ("magnoliya", "магнолия"),
        ("lola daraxti", "лола дарахти")
    ],
    "Tez o‘suvchilar": [
        ("terak", "терак"),
        ("tol (iva)", "тол (ива)"),
        ("majnuntol", "мажнунтол"),
        ("pavlovniya", "павловния")
    ],
    "Yong‘oqmevalilar": [
        ("yong‘oq", "ёнгок"),
        ("achchiq bodom", "аччиқ бодом"),
        ("shirin bodom", "ширин бодом"),
        ("pekan", "пекан"),
        ("pista", "писта"),
        ("funduk", "фундук")
    ],
    "Mevalilar": [
        ("o‘rik (abrikos)", "ўрик (абрикос)"),
        ("shaftoli", "шафтоли"),
        ("olchcha (vishnya)", "олча (вишневый)"),
        ("olxuri, qorali GAYLOLU", "олхури, қорали ГАЙЛОЛУ"),
        ("pissarda olxurisi", "писсарда олхуриси"),
        ("gilos (vishnya)", "гилос  (вышня)"),
        ("magalepka gilos", "магалепка гилос"),
        ("xurmo", "хурмо"),
        ("olma", "олма"),
        ("bexi", "бехи"),
        ("nok (murut)", "нок (мурут)"),
        ("uzum (tok)", "узум (ток)"),
        ("anor", "анор"),
        ("anjir", "анжир"),
        ("qizil do‘lona", "қизил дўлана"),
        ("tut", "тут"),
        ("chappa tut", "чаппа тут"),
        ("jiyda", "жийда"),
        ("non jiyda", "нон жийда"),
        ("chilonjiyda (unabi)", "чилонжийда (унаби)"),
        ("palma", "Палма"),
        ("limon", "лимон")
    ],
    "Cho'l o'simliklari": [
        ("Saksovul", "Саксаул")
    ],
    "Ignabarglilar": [
        ("tyanshan qora qarag‘ayi", "тяншан қора қарағайи"),
        ("zarafshon archasi", "Зарафшон арчаси"),
        ("virgin archa", "виргин арча"),
        ("sharq tuya", "шарқ туя"),
        ("kompakt tuya", "компакт туя"),
        ("qrim qarag‘ayi", "қрим қарағайи"),
        ("eldor qarag‘ayi", "эльдор қарағайи"),
        ("sarvi (kiparis)", "сарви (кипарис)"),
        ("tog‘ archa", "тоғ арча")
    ],
    "Buta va gullar": [
        ("na‘matak (shipovnik)", "наъматак (шиповник)"),
        ("amorfa", "аморфа"),
        ("ligustrum (biryuchina)", "лигуструм (бирючина)"),
        ("beresklet", "бересклет"),
        ("yapon bexi", "япон бехи"),
        ("magoniya", "магония"),
        ("forzitsiya", "форзиция"),
        ("samshit", "самшит"),
        ("sireni", "сирень"),
        ("hind sireni", "ҳинд сирени"),
        ("atirgul", "атиргул"),
        ("suriya atirguli (gibiskus)", "сурия атиргули (гибискус)"),
        ("tsizalpiniya", "цизалпиния"),
        ("chakanda (oblepixa)", "чаканда (облепиха)"),
        ("ispan drek", "испан дрок"),
        ("sumax", "сумах"),
        ("yukka", "юкка"),
        ("smorodina", "смородина"),
        ("arxideya", "архидея"),
        ("ryabina", "рябина"),
        ("pirakanta", "пираканта"),
        ("lovanda", "лованда"),
        ("zirk", "зирк"),
        ("boshqalar", "бошқалар")
    ]
}

class Command(BaseCommand):
    help = "Create Plants with parents for specific statement (safe & idempotent)"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Creating plants with parent categories...")

        try:
            statement = Statement.objects.get(name_uz="Ko'chatxona va Niholxona Jami")
        except Statement.DoesNotExist:
            self.stderr.write("❌ Statement not found.")
            return

        total_created = 0

        for parent_key, children in PLANTS_STRUCTURE.items():
            translations = PARENT_NAMES.get(parent_key)

            if not translations:
                self.stderr.write(f"⚠️ Parent '{parent_key}' not found in PARENT_NAMES")
                continue

            # ✅ PARENT (tepada yoziladi)
            parent, parent_created = Plant.objects.get_or_create(
                name=parent_key,
                parent=None,
                statement=statement,
                defaults={
                    build_localized_fieldname("name", "uz"): translations["uz"],
                    build_localized_fieldname("name", "ru"): translations["ru"],
                },
            )

            if parent_created:
                total_created += 1
                self.stdout.write(f"➕ Parent created: {translations['uz']}")

            # ✅ CHILDREN (pastda)
            for name_uz, name_ru in children:
                child, child_created = Plant.objects.get_or_create(
                    name=name_uz,
                    parent=parent,
                    statement=statement,
                    defaults={
                        build_localized_fieldname("name", "uz"): name_uz,
                        build_localized_fieldname("name", "ru"): name_ru,
                    },
                )

                if child_created:
                    total_created += 1
                    self.stdout.write(f"   ➕ Plant created: {name_uz}")

        self.stdout.write(
            self.style.SUCCESS(f"✅ Done. Total new plants created: {total_created}")
        )
