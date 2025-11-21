# apps/users/middleware.py
from django.utils import timezone
from apps.users.models.users import CustomUser

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            CustomUser.objects.filter(id=request.user.id).update(
                last_activity=timezone.now()
            )
        return self.get_response(request)
