# apps/users/admin_forms.py
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.users.models.users import CustomUser


class CustomUserAdminForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = "__all__"

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            return password

        # Mavjud user tahrirlashda — agar password o'zgarmagan bo'lsa, tekshirmaslik
        if self.instance and self.instance.pk:
            # Django admin hashed passwordni saqlaydi, agar qiymat o'sha bo'lsa — o'zgarmagan
            if password == self.instance.password:
                return password

        try:
            validate_password(password, user=self.instance)
        except ValidationError as e:
            raise ValidationError(e.messages)

        return password

    def clean_region_user_orgs(self):
        orgs = self.cleaned_data.get("region_user_orgs")
        role = self.cleaned_data.get("role")
        region = self.cleaned_data.get("region")

        # Tekshiruv faqat HUDUDIY_BOSHQARMA uchun
        if role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            if not region:
                raise ValidationError("Hududiy boshqarma uchun region majburiy")

            if not orgs or not orgs.exists():
                raise ValidationError("Kamida bitta tashkilot tanlanishi shart")

            invalid_orgs = orgs.exclude(region=region)
            if invalid_orgs.exists():
                raise ValidationError(
                    "Biriktirilgan tashkilotlar foydalanuvchi regioniga mos emas"
                )

        return orgs

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        region = cleaned_data.get("region")
        orgs = cleaned_data.get("region_user_orgs")

        if role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            if region and orgs:
                invalid_orgs = orgs.exclude(region=region)
                if invalid_orgs.exists():
                    raise ValidationError({
                        "region_user_orgs": "Biriktirilgan tashkilotlar foydalanuvchi regioniga mos emas"
                    })

        return cleaned_data
