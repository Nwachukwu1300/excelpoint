from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile
from skills.models import Skill

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

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile details."""
    
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(max_length=254, required=False)
    current_role = forms.CharField(max_length=100, required=False)
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'linkedin_profile', 'github_profile']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'linkedin_profile': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/your-profile'}),
            'github_profile': forms.URLInput(attrs={'placeholder': 'https://github.com/your-username'}),
        }
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            # Update User model fields
            user = profile.user
            user.first_name = self.cleaned_data.get('first_name', user.first_name)
            user.last_name = self.cleaned_data.get('last_name', user.last_name)
            user.email = self.cleaned_data.get('email', user.email)
            user.current_role = self.cleaned_data.get('current_role', user.current_role)
            user.save()
        return profile

class CustomSkillForm(forms.Form):
    """Form for adding custom skills."""
    
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter skill name (e.g., Python, Project Management)',
        })
    )
    
    category = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter skill category (e.g., Technical, Soft Skills)',
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a brief description or note (optional)',
            'rows': 3,
        })
    )
    
    def clean_name(self):
        name = self.cleaned_data['name']
        # Check for existing skill with same name owned by this user
        # This validation will be done in the view with access to request.user
        return name
