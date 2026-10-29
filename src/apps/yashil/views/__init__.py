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
from .cancel import (
    CancelAgreeView,
    CancelApproveView,
    CancelDetailView,
    CancelListView,
    CancelRejectView,
    OrderCancelView,
)
from .documents import (
    DocumentVersionHtmlView,
    DocumentVersionPdfView,
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
    StockOrganizationsView,
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
    "CancelAgreeView", "CancelApproveView", "CancelDetailView", "CancelListView", "CancelRejectView", "OrderCancelView",
    "ActAttachmentDeleteView", "ActAttachmentsView", "ActCancelView", "ActDetailView", "ActListView", "ActReturnView",
    "ActSignTaskView", "ActSignView", "OrderActsCreateView",
    "DocumentVersionHtmlView", "DocumentVersionPdfView", "DocumentVersionView", "NotificationListView", "NotificationReadAllView",
    "NotificationReadView", "PublicVerifyView", "OrderAcceptView", "OrderAttachmentDeleteView", "OrderAttachmentsView",
    "OrderDetailView", "OrderDocumentView", "OrderEventsView", "OrderForwardView", "OrderListCreateView",
    "OrderReturnView", "OrderReviewView", "OrderSubmitView",
    "CalendarDueView", "CalendarListView", "CatalogListView", "DistrictListView", "MahallaListView", "MeView",
    "ObjectTypeListView", "RegionListView", "SeasonListView", "SuppliersForMahallaView",
    "ServiceCapacityView", "StockMovementListView", "StockOrganizationsView", "StockOpeningView", "StockReceiptView", "StockReturnInView",
    "StockReversalApproveView", "StockReversalRejectView", "StockReversalRequestView", "StockSummaryView",
]
