"""Kabinet xabarnomalari (TZ §22.4): kimga va nima yuboriladi."""
from apps.yashil.models import YashilMembership, YashilNotification
from apps.yashil.services.scope import memberships_active_for_target

T = YashilMembership.MemberType


def notify_memberships(memberships, *, kind: str, title: str, body: str = "", order=None):
    rows = [
        YashilNotification(recipient_user_id=m.user_id, membership=m, kind=kind, title=title, body=body[:1000], order=order)
        for m in memberships
    ]
    return YashilNotification.objects.bulk_create(rows)


def notify_mahalla(order, **kw):
    return notify_memberships(memberships_active_for_target(T.MAHALLA, mahalla_id=order.mahalla_id), order=order, **kw)


def notify_union(order, **kw):
    if not order.union_unit_id:
        return []
    return notify_memberships(memberships_active_for_target(T.UNION, union_unit_id=order.union_unit_id), order=order, **kw)


def notify_supplier(order, **kw):
    return notify_memberships(memberships_active_for_target(T.SUPPLIER, organization_id=order.supplier_org_id), order=order, **kw)


def notify_observers(order, **kw):
    return notify_memberships(memberships_active_for_target(T.OBSERVER), order=order, **kw)
