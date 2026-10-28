from .acts import (
    ActAttachmentDeleteView,
    ActAttachmentsView,
    ActCancelView,
    ActDetailView,
    ActListView,
    ActReturnView,
    ActSignTaskView,
    ActSignView,
    OrderActsCreateView,
)
from .documents import (
    DocumentVersionHtmlView,
    DocumentVersionView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PublicVerifyView,
)
from .orders import (
    OrderAcceptView,
    OrderAttachmentDeleteView,
    OrderAttachmentsView,
    OrderDetailView,
    OrderDocumentView,
    OrderEventsView,
    OrderForwardView,
    OrderListCreateView,
    OrderReturnView,
    OrderReviewView,
    OrderSubmitView,
)
from .stock import (
    ServiceCapacityView,
    StockMovementListView,
    StockOpeningView,
    StockReceiptView,
    StockReturnInView,
    StockReversalApproveView,
    StockReversalRejectView,
    StockReversalRequestView,
    StockSummaryView,
)
from .reference import (
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

__all__ = [
    "ActAttachmentDeleteView", "ActAttachmentsView", "ActCancelView", "ActDetailView", "ActListView", "ActReturnView",
    "ActSignTaskView", "ActSignView", "OrderActsCreateView",
    "DocumentVersionHtmlView", "DocumentVersionView", "NotificationListView", "NotificationReadAllView",
    "NotificationReadView", "PublicVerifyView", "OrderAcceptView", "OrderAttachmentDeleteView", "OrderAttachmentsView",
    "OrderDetailView", "OrderDocumentView", "OrderEventsView", "OrderForwardView", "OrderListCreateView",
    "OrderReturnView", "OrderReviewView", "OrderSubmitView",
    "CalendarDueView", "CalendarListView", "CatalogListView", "DistrictListView", "MahallaListView", "MeView",
    "ObjectTypeListView", "RegionListView", "SeasonListView", "SuppliersForMahallaView",
    "ServiceCapacityView", "StockMovementListView", "StockOpeningView", "StockReceiptView", "StockReturnInView",
    "StockReversalApproveView", "StockReversalRejectView", "StockReversalRequestView", "StockSummaryView",
]
