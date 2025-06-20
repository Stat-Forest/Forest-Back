from apps.base.serializers import CustomSerializer
from apps.base.views import CustomListAPIView
from apps.users.models import CustomUser


class Gold(CustomListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomSerializer