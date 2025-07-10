from django.core.management.base import BaseCommand
from apps.reports.models import StatementColumn, Plant, ColumnPlant


class Command(BaseCommand):
    help = "❗️Faqat 'Ko‘chat-ilovasi' va 'Nihol-ilovasi' ostidagi leaf-columnlarga (tashkilot emas) har bir plantni faqat 1 marta ColumnPlant sifatida bog'laydi"

    def handle(self, *args, **kwargs):
        allowed_ilova_titles = ["Ko‘chat-ilovasi", "Nihol-ilovasi"]
        all_plants = list(Plant.objects.all())
        created_count = 0
        used_plant_ids = set(ColumnPlant.objects.values_list("plant_id", flat=True))

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
                    if plant.id in used_plant_ids:
                        continue  # allaqachon boshqa columnga bog‘langan
                    obj, created = ColumnPlant.objects.get_or_create(
                        column=column,
                        plant=plant
                    )
                    if created:
                        used_plant_ids.add(plant.id)
                        created_count += 1
                        print(f"✅ Yaratildi: Ilova = {ilova_title}, Column = {column.title_uz}, Plant = {plant.name}")
                    else:
                        print(f"↪️ Mavjud: Ilova = {ilova_title}, Column = {column.title_uz}, Plant = {plant.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\n🏁 Yakuniy natija: {created_count} ta yangi ColumnPlant yozuvi qo‘shildi"
        ))

    def get_leaf_columns_under(self, root):
        """
        Root (ilova) ostidagi barcha leaf-columnlarni (va is_organization=False bo‘lganlarini) qaytaradi.
        """
        all_columns = StatementColumn.objects.filter(statement=root.statement)
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
