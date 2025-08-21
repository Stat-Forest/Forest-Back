from rest_framework import generics, status
from rest_framework.response import Response
from apps.reports.models import Plan
from apps.reports.serializers import PlanSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Plan"])
class PlanUpdateView(generics.UpdateAPIView):
    """
    Plan obyektini update qilish uchun generic view.
    Statement maydoni update qilinmaydi.
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # statement update qilinmasin
        data = request.data.copy()
        data.pop("statement", None)

        serializer = self.get_serializer(
            instance, data=data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Plan"])
class PlanRetrieveView(generics.RetrieveAPIView):
    """
    Plan obyektini faqat GET orqali olish uchun view.
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
