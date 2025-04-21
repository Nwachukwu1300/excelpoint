from django import forms
from .models import CareerRole

class RoleSelectionForm(forms.Form):
    """Form for selecting a target career role."""
    
    role = forms.ModelChoiceField(
        queryset=CareerRole.objects.all().order_by('name'),
        empty_label="Select your dream role",
        required=True,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
                'id': 'role-select'
            }
        )
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].label = "Target Career Role"
