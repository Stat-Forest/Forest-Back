class DRFHistoryMixin:
    """DRF viewlar uchun universal log mixin."""

    def perform_create(self, serializer):
        obj = serializer.save(_history_user=self.request.user)
        return obj

    def perform_update(self, serializer):
        obj = serializer.save(_history_user=self.request.user)
        return obj

    def perform_destroy(self, instance):
        instance._history_user = self.request.user
        instance.delete()
