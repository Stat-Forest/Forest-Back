# apps/logs/mixins.py
class AdminHistoryMixin:
    """Admin log uchun universal mixin."""
    def save_model(self, request, obj, form, change):
        obj._history_user = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj._history_user = request.user
        super().delete_model(request, obj)
