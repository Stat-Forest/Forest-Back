from django.utils.translation import gettext_lazy as _
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report
from apps.reports.serializers import ReportAcceptSerializer
# from apps.reports.permissions import CanAcceptReport


@extend_schema(tags=["Reports Status Update"])
class ReportAcceptAPIView(UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportAcceptSerializer
    # permission_classes = [CanAcceptReport]

    def get_object(self, report_id):
        try:
            return self.get_queryset().get(id=report_id)
        except Report.DoesNotExist:
            raise CustomExceptionError(
                code=404,
                detail={"report": _("Report not found.")}
            )

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        report_id = request.data.get("id")
        if not report_id:
            raise CustomExceptionError(
                code=400,
                detail={"id": ["This field is required."]}
            )

        instance = self.get_object(report_id)
        serializer = self.get_serializer(
            data=request.data,
            context={"report_instance": instance}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "id": str(instance.id),
            "status": instance.status,
            "accepted_at": instance.accepted_at
        })
