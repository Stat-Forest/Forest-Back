from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.billing.views import (
    ActivityTypeListView,
    BolimListView,
    ContractFileViewSet,
    ContractViewSet,
    DistrictListView,
    LandTypeListView,
    PrivilegeTypeListView,
    RegionListView,
    RenterListView,
    XojalikKonturViewSet,
    XojalikListView,
    XojalikLocationViewSet,
)

router = SimpleRouter()
router.register("contracts", ContractViewSet, basename="billing-contract")
router.register("contract-files", ContractFileViewSet, basename="billing-contract-file")
router.register("xojalik-locations", XojalikLocationViewSet, basename="billing-xojalik-location")
router.register("xojalik-konturs", XojalikKonturViewSet, basename="billing-xojalik-kontur")

urlpatterns = [
    path("regions/", RegionListView.as_view(), name="billing-region-list"),
    path("districts/", DistrictListView.as_view(), name="billing-district-list"),
    path("xojaliklar/", XojalikListView.as_view(), name="billing-xojalik-list"),
    path("bolimlar/", BolimListView.as_view(), name="billing-bolim-list"),
    path("land-types/", LandTypeListView.as_view(), name="billing-land-type-list"),
    path("activity-types/", ActivityTypeListView.as_view(), name="billing-activity-type-list"),
    path("privilege-types/", PrivilegeTypeListView.as_view(), name="billing-privilege-type-list"),
    path("renters/", RenterListView.as_view(), name="billing-renter-list"),
    path("", include(router.urls)),
]
