import threading

_thread_locals = threading.local()

def get_current_user():
    """ThreadLocal orqali joriy foydalanuvchini qaytaradi"""
    return getattr(_thread_locals, "user", None)


class CurrentUserMiddleware:
    """Har bir request uchun foydalanuvchini global contextda saqlaydi"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        try:
            return self.get_response(request)
        finally:
            # So'rov tugagach tozalaymiz — aks holda shu thread'dagi keyingi ish
            # (boshqa so'rov, test) eski foydalanuvchi nomidan log yozib qo'yadi.
            _thread_locals.user = None


def get_history_user(request):
    if request.path.startswith("/admin/") or request.path.startswith("/api/v1/authentications/login/"):
        return getattr(request, "user", None)
    return None