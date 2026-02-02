def apply_deadline_filter(queryset, period, params):
    value = params.get(period)
    if not value:
        return queryset.none()

    return queryset.filter(
        deadline__submit_at=value,
        statement__period=period
    )
