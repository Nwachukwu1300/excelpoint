from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
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
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'current_role', 
                 'experience_level', 'bio', 'linkedin_profile', 'github_profile')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'current_role': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_level': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'linkedin_profile': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/username'}),
            'github_profile': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username'}),
        }

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
