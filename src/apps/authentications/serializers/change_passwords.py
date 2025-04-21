from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise CustomExceptionError(code=404, detail="password was mistake")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise CustomExceptionError(code=404, detail="passwords was not equal, with new_password and confirm_password.")
        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user