from apps.reports.models import StatementColumn


def get_leaf_columns_under_ilova_root(root):
    """
    Root (ilova) ostidagi barcha leaf-columnlarni (va is_organization=False bo‘lganlarini) qaytaradi.
    Optimallashtirilgan: 1ta query bilan ishlaydi.
    """
    all_columns = (
        StatementColumn.objects
        .filter(statement=root.statement)
        .select_related('parent')  # kerak bo‘lsa
        .prefetch_related('children')  # children.exists() o‘rniga
    )

    root_id = root.id
    result = []

    for col in all_columns:
        # faqatgina root ostidagilarni tekshiramiz
        current = col.parent
        is_under_root = False
        while current:
            if current.id == root_id:
                is_under_root = True
                break
            current = current.parent

        if is_under_root and not col.children.all() and not col.is_organization:
            result.append(col)

    return result
