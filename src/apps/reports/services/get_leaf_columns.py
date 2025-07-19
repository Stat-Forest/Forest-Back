from apps.reports.models import StatementColumn


def get_leaf_columns_under_ilova_root(root):
    """
    Root (ilova) ostidagi barcha leaf-columnlarni (va is_organization=False bo‘lganlarini) optimized queryset sifatida qaytaradi.
    Faqat root`ning bevosita farzandlaridan pastdagilar (2-daraja va chuqurroq) olinadi.
    """

    return (
        StatementColumn.objects.filter(
            is_organization=False,
            parent__isnull=False,
            children__isnull=True,
            statement=root.statement
        ).select_related('parent').prefetch_related('children')
    )
