from rest_framework.views import APIView
from rest_framework.response import Response
from apps.reports.models import StatementColumn

class PlaneStatementColumnListAPIView(APIView):

    def get(self, request, *args, **kwargs):
        user = request.user

        columns = StatementColumn.objects.filter(
            statement__parent=user.statement,
            is_plane=True
        )

        return Response(columns)
