from django.core.management.base import BaseCommand
from apps.reports.models import Plant


PLANTS_STRUCTURE = {
    "Япроқбарглилар": [
        "багрянник", "эман черешч (дуб)", "эман пирамид (дуб)", "қайрогоч (вяз)",
        "сада қайроғоч (гужум)", "шумтол (ясень)", "айлант", "саваттол",
        "гледичия", "чинор", "япон сафораси", "каштан", "катальпа",
        "хило каталпа", "оқ қайин (берёза)", "заранг (клен)", "ипак акация",
        "акация", "маклюра", "липа", "қогоз дарахт", "совун дарахти",
        "магнолия", "лола дарахти"
    ],
    "Тез ўсувчилар": ["терак", "тол (ива)", "мажнунтол", "павловния"],
    "Ёнғоқмевалилар": ["ёнгок", "аччиқ бодом", "ширин бодом", "пекан", "писта", "фундук"],
    "Мевалилар": [
        "ўрик (абрикос)", "шафтоли", "олча (вишневый)", "олхури, қорали ГАЙЛОЛУ",
        "писсарда олхуриси", "гилос  (вышня)", "магалепка гилос", "хурмо", "олма",
        "бехи", "нок (мурут)", "узум (ток)", "анор", "анжир", "қизил дўлана",
        "тут", "чаппа тут", "жийда (лох)", "нон жийда", "чилонжийда (унаби)",
        "Палма", "лимон"
    ],
    "Игнабарглилар": [
        "тяншан қора қарағайи", "Зарафшон арчаси", "виргин арча", "шарқ туя",
        "компакт туя", "қрим қарағайи", "эльдор қарағайи", "сарви (кипарис)", "тоғ арча"
    ],
    "Бута ва гуллар": [
        "наъматак (шиповник)", "аморфа", "лигуструм (бирючина)", "бересклет",
        "япон бехи", "магония", "форзиция", "самшит", "сирень", "ҳинд сирени",
        "атиргул", "сурия атиргули (гибискус)", "цизалпиния", "чаканда (облепиха)",
        "испан дрок", "сумах", "юкка", "смородина", "архидея", "рябина",
        "пираканта", "лованда", "зирк", "бошқалар"
    ]
}


class Command(BaseCommand):
    help = "Create Plant categories and their children from PLANTS_STRUCTURE"

    def handle(self, *args, **kwargs):
        self.stdout.write(">>> Creating Plants...")

        total_created = 0
        parent_names = []

        for parent_name, children in PLANTS_STRUCTURE.items():
            parent, _ = Plant.objects.get_or_create(name=parent_name, parent=None)
            parent_names.append(parent_name)
            created_in_this_group = 0

            for child_name in children:
                plant, created = Plant.objects.get_or_create(name=child_name, parent=parent)
                if created:
                    self.stdout.write(f"  ✓ {child_name} (parent: {parent_name})")
                    created_in_this_group += 1

            self.stdout.write(f"✔ {parent_name}: {created_in_this_group} child(ren)")
            total_created += created_in_this_group

        XUJALIK_DUX_NAME = "Хўжалик ДЎХ"
        xujalik_dux, created = Plant.objects.get_or_create(name=XUJALIK_DUX_NAME, parent=None)
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created top-level plant: {XUJALIK_DUX_NAME}"))
        else:
            self.stdout.write(f"• {XUJALIK_DUX_NAME} already exists")

        self.stdout.write(self.style.SUCCESS(f"✓ All done. Total children created: {total_created}"))
