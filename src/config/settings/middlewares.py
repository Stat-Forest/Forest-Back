from django.http import HttpResponseForbidden


ADMIN_ALLOWED_IPS = {
    # "172.18.0.1",   # Docker local
    # production IP'lar keyin qo‘shiladi
}


class AdminIPWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            ip = self.get_client_ip(request)

            print("ADMIN ACCESS TRY FROM IP:", ip)

            if ip not in ADMIN_ALLOWED_IPS:
                return HttpResponseForbidden("❌ Access to admin is restricted")

        return self.get_response(request)

    def get_client_ip(self, request):
        # nginx bo‘lsa
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        # docker / local
        return request.META.get("REMOTE_ADDR")
