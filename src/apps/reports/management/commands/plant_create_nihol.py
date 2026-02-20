from django.core.management.base import BaseCommand
from django.db import transaction
from modeltranslation.utils import build_localized_fieldname

from apps.reports.models import Plant, Statement

PARENT_NAMES = {
    "Yaproqbarglilar": {
        "uz": "Yaproqbarglilar",
        "ru": "Лиственные"
    },
    "Tez o‘suvchilar": {
        "uz": "Tez o‘suvchilar",
        "ru": "Быстрорастущие"
    },
    "Yong‘oqmevalilar": {
        "uz": "Yong‘oqmevalilar",
        "ru": "Орехоплодные"
    },
    "Mevalilar": {
        "uz": "Mevalilar",
        "ru": "Плодовые"
    },
    "Cho'l o'simliklari": {
        "uz": "Cho'l o'simliklari",
        "ru": "Пустынные растения"
    },
    "Ignabarglilar": {
        "uz": "Ignabarglilar",
        "ru": "Хвойные"
    },
    "Buta va gullar": {
        "uz": "Butalar va gullar",
        "ru": "Кустарники и цветы"
    }
}

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
        ("lola daraxti", "лола дарахти"),
        ("ginkgo biloba", "Гинкго билоба"),
        ("kanada bundugi", "Канада бундуги"),
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
        ("Saksovul", "Саксаул"),
        ("Cherkez", "Черкез"),
        ("Yulg‘un", "Юлғун"),
        ("Qoraburoq", "Қорабуроқ"),
        ("Qandim", "Қандим"),
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
    help = "Safe plant sync for Ko‘chat va Nihol (no duplicates, only new added)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("🚀 Syncing Plants for Ko‘chat va Nihol...")

        try:
            statement = Statement.objects.get(name_uz="Ko‘chat va Nihol")
        except Statement.DoesNotExist:
            self.stderr.write("❌ Statement 'Ko‘chat va Nihol' not found.")
            return

        created = 0
        updated = 0

        # ======================
        # PARENTS
        # ======================

        for parent_key, children in PLANTS_STRUCTURE.items():

            parent_data = PARENT_NAMES[parent_key]
            parent_uz = parent_data["uz"]
            parent_ru = parent_data["ru"]

            parent = (
                Plant.objects
                .filter(parent__isnull=True, statement=statement)
                .filter(name__iexact=parent_uz)
                .first()
            )

            if not parent:
                parent = Plant.objects.create(
                    name=parent_uz,
                    parent=None,
                    statement=statement
                )
                created += 1
                self.stdout.write(f"➕ Parent created: {parent_uz}")

            changed = False

            if getattr(parent, build_localized_fieldname("name", "uz")) != parent_uz:
                setattr(parent, build_localized_fieldname("name", "uz"), parent_uz)
                changed = True

            if getattr(parent, build_localized_fieldname("name", "ru")) != parent_ru:
                setattr(parent, build_localized_fieldname("name", "ru"), parent_ru)
                changed = True

            if parent.statement_id != statement.id:
                parent.statement = statement
                changed = True

            if changed:
                parent.save()
                updated += 1
                self.stdout.write(f"🔁 Parent updated: {parent_uz}")

            # ======================
            # CHILDREN
            # ======================

            for uz_name, ru_name in children:

                child = (
                    Plant.objects
                    .filter(parent=parent, statement=statement)
                    .filter(name__iexact=uz_name)
                    .first()
                )

                if not child:
                    child = Plant.objects.create(
                        name=uz_name,
                        parent=parent,
                        statement=statement
                    )
                    created += 1
                    self.stdout.write(f"   ➕ Created: {uz_name}")

                changed = False

                if getattr(child, build_localized_fieldname("name", "uz")) != uz_name:
                    setattr(child, build_localized_fieldname("name", "uz"), uz_name)
                    changed = True

                if getattr(child, build_localized_fieldname("name", "ru")) != ru_name:
                    setattr(child, build_localized_fieldname("name", "ru"), ru_name)
                    changed = True

                if child.statement_id != statement.id:
                    child.statement = statement
                    changed = True

                if changed:
                    child.save()
                    updated += 1
                    self.stdout.write(f"   🔁 Updated: {uz_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Done | Created: {created} | Updated: {updated}"
            )
        )