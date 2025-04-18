from django import forms

from apps.general.models import Organization
from apps.reports.models import Deadline


class CustomSelectMultiple(forms.SelectMultiple):
    """SelectMultiple widget that disables 'All Organizations' option"""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if str(value) == DeadlineAdminForm.ALL_ORG_ID:
            option['attrs']['disabled'] = True
        return option


class DeadlineAdminForm(forms.ModelForm):
    ALL_ORG_ID = "-1"

    organization = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        widget=CustomSelectMultiple,
        required=False
    )

    class Meta:
        model = Deadline
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Original choices from queryset
        original_choices = list(self.fields['organization'].choices)

        # Add disabled "All Organizations" option at the top
        all_option = [(self.ALL_ORG_ID, 'All Organizations (selects all)')]
        self.fields['organization'].choices = all_option + original_choices

    def _clean_form(self):
        """
        Override _clean_form to handle 'All Organizations' logic before validation.
        Replaces -1 with all organization IDs in self.data
        """
        selected_ids = self.data.getlist('organization')

        if self.ALL_ORG_ID in selected_ids:
            all_ids = [str(org.id) for org in Organization.objects.all()]
            mutable_data = self.data.copy()
            mutable_data.setlist('organization', all_ids)
            self.data = mutable_data

        super()._clean_form()
