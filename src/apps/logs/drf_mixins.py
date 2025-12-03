class DRFHistoryMixin:
    """DRF viewlar uchun universal log mixin."""

    def perform_create(self, serializer):
        obj = serializer.save()
        obj._history_user = self.request.user
        obj.save()
        return obj

    def perform_update(self, serializer):
        obj = serializer.save()
        obj._history_user = self.request.user
        obj.save()
        return obj

    def perform_destroy(self, instance):
        instance._history_user = self.request.user
        instance.delete()
