from rest_framework.generics import GenericAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound

from apps.reports.models import Report
from apps.reports.permissions import CanSendReport
from apps.reports.serializers import ReportSendSerializer

class ReportSendAPIView(UpdateModelMixin, GenericAPIView):

    queryset = Report.objects.all()
    serializer_class = ReportSendSerializer
    # permission_classes = [IsAuthenticated, CanSendReport]

    def get_object(self):
        report_id = self.request.data.get('id')
        if not report_id:
            raise ValidationError({'id': 'This field is required.'})
        try:
            obj = self.get_queryset().get(id=report_id)
        except Report.DoesNotExist:
            raise NotFound('Report not found.')
        self.check_object_permissions(self.request, obj)
        return obj

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
