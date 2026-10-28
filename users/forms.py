from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile

class RegistrationForm(UserCreationForm):
    """Form for user registration."""
    
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to default fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})


class SettingsForm(forms.ModelForm):
    """Basic settings form to edit name and education level."""
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    education_level = forms.ChoiceField(required=False, choices=[('', '— Select —')] + UserProfile.EDUCATION_LEVEL_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = UserProfile
        fields = ['education_level']
