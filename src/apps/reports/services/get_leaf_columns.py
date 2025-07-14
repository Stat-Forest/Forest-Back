from apps.reports.models import StatementColumn


def get_leaf_columns_under_ilova_root(root):
    """
    Root (ilova) ostidagi barcha leaf-columnlarni (va is_organization=False bo‘lganlarini) optimized queryset sifatida qaytaradi.
    Faqat root`ning bevosita farzandlaridan pastdagilar (2-daraja va chuqurroq) olinadi.
    """
    first_level_children = StatementColumn.objects.filter(parent=root)

    return (
        StatementColumn.objects.filter(
            is_organization=False,
            children__isnull=True,
            parent__in=StatementColumn.objects.filter(parent__in=first_level_children)
        ).select_related('parent').prefetch_related('children')
    )
