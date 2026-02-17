from rest_framework.exceptions import NotAuthenticated


class DRFHistoryMixin:
    """DRF viewlar uchun universal log mixin."""

    def _get_user_or_fail(self):
        user = getattr(self.request, "user", None)

        if not user or not user.is_authenticated:
            raise NotAuthenticated("Authentication required to modify data.")

        return user

    def perform_create(self, serializer):
        obj = serializer.save()

        user = self._get_user_or_fail()
        obj._history_user = user

        # history lib uchun trigger bolishi yetarli
        obj.save(update_fields=[])

        return obj

    def perform_update(self, serializer):
        obj = serializer.save()

        user = self._get_user_or_fail()
        obj._history_user = user

        obj.save(update_fields=[])

        return obj

    def perform_destroy(self, instance):
        user = self._get_user_or_fail()

        instance._history_user = user
        instance.delete()