from django.urls import path

from apps.yashil.views import (
    CalendarDueView,
    CalendarListView,
    CatalogListView,
    DistrictListView,
    MahallaListView,
    MeView,
    ObjectTypeListView,
    RegionListView,
    SeasonListView,
    SuppliersForMahallaView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="yashil-me"),
    path("reference/regions/", RegionListView.as_view(), name="yashil-regions"),
    path("reference/districts/", DistrictListView.as_view(), name="yashil-districts"),
    path("reference/mahallas/", MahallaListView.as_view(), name="yashil-mahallas"),
    path("reference/seasons/", SeasonListView.as_view(), name="yashil-seasons"),
    path("reference/object-types/", ObjectTypeListView.as_view(), name="yashil-object-types"),
    path("suppliers/for-mahalla/<uuid:mahalla_id>/", SuppliersForMahallaView.as_view(), name="yashil-suppliers-for-mahalla"),
    path("catalog/", CatalogListView.as_view(), name="yashil-catalog"),
    path("calendar/", CalendarListView.as_view(), name="yashil-calendar"),
    path("calendar/due/", CalendarDueView.as_view(), name="yashil-calendar-due"),
]
