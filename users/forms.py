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

    def clean_email(self):
        return _unused_email(self.cleaned_data['email'])


def _unused_email(email, user=None):
    """One account per email, ignoring case: Google sign-in and any future recovery rely on it."""
    taken = User.objects.filter(email__iexact=email)
    if user is not None:
        taken = taken.exclude(pk=user.pk)
    if taken.exists():
        raise forms.ValidationError('An account with this email already exists.')
    return email


class SettingsForm(forms.ModelForm):
    """Basic settings form to edit name and education level."""
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), error_messages={'required': 'Enter an email address.'})
    education_level = forms.ChoiceField(required=False, choices=[('', '— Select —')] + UserProfile.EDUCATION_LEVEL_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = UserProfile
        fields = ['education_level']

    def clean_email(self):
        email, user = self.cleaned_data['email'], self.instance.user
        # Only a change is checked, so an account that already shares an email can still save its other settings
        return email if email.lower() == (user.email or '').lower() else _unused_email(email, user)
