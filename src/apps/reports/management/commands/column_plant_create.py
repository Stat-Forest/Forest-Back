from django.core.management.base import BaseCommand
from apps.reports.models import StatementColumn, Plant, ColumnPlant


class Command(BaseCommand):
    help = "Ko‘chat va Nihol ilovalari ostidagi barcha leaf-columnlarga 96 ta plantni biriktiradi"

    def handle(self, *args, **kwargs):
        allowed_ilova_titles = ["Ko‘chat-ilovasi", "Nihol-ilovasi"]
        all_plants = list(Plant.objects.all())  # 96 ta plant (parent + child)
        created_count = 0

        for ilova_title in allowed_ilova_titles:
            try:
                ilova_root = StatementColumn.objects.get(
                    title_uz__iexact=ilova_title,
                    parent__isnull=True
                )
            except StatementColumn.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ {ilova_title} topilmadi."))
                continue

            leaf_columns = self.get_leaf_columns_under(ilova_root)

            for column in leaf_columns:
                for plant in all_plants:
                    obj, created = ColumnPlant.objects.get_or_create(
                        column=column,
                        plant=plant
                    )
                    if created:
                        created_count += 1
                        print(f"✅ Yaratildi: {ilova_title} | Column = {column.title_uz} | Plant = {plant.name}")
                    else:
                        print(f"↪️ Mavjud: {ilova_title} | Column = {column.title_uz} | Plant = {plant.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\n🏁 Yakuniy natija: {created_count} ta yangi ColumnPlant yozuvi qo‘shildi"
        ))

    def get_leaf_columns_under(self, root):
        all_columns = StatementColumn.objects.filter(statement=root.statement).select_related("parent")
        leafs = []
        for col in all_columns:
            current = col.parent
            while current:
                if current.id == root.id:
                    if not col.children.exists() and not col.is_organization:
                        leafs.append(col)
                    break
                current = current.parent
        return leafs
