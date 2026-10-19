# apps/users/admin_forms.py
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.users.models.users import CustomUser


class CustomUserAdminForm(forms.ModelForm):
    """Tahrirlash formasi: parol hash'i faqat ko'rsatiladi (tahrirlanmaydi, audit A9);
    yangi parol alohida maydon orqali o'rnatiladi."""

    password = ReadOnlyPasswordHashField(
        label="Parol",
        help_text="Parol hash'langan holda saqlanadi. Yangi parol qo'yish uchun quyidagi maydonni to'ldiring.",
    )
    new_password = forms.CharField(
        label="Yangi parol",
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Bo'sh qoldirilsa parol o'zgarmaydi.",
    )

    class Meta:
        model = CustomUser
        fields = "__all__"

    def clean_password(self):
        # ReadOnlyPasswordHashField: foydalanuvchi nima yubormasin, eski hash qoladi
        return self.initial.get("password")

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password:
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


class CustomUserCreationForm(forms.ModelForm):
    """Yaratish formasi: parol ikki marta kiritiladi va hash'lanadi."""

    password1 = forms.CharField(label="Parol", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Parol (takror)", strip=False, widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        exclude = ("password",)

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Parollar mos kelmadi")
        try:
            validate_password(p2, user=self.instance)
        except ValidationError as e:
            raise ValidationError(e.messages)
        return p2
