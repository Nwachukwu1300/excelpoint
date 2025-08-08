from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile, UserAchievement, UserCertification, UserEducation

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
    """Form for editing user profile information."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'current_role', 'experience_level', 'bio', 'linkedin_profile', 'github_profile']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'current_role': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_level': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'linkedin_profile': forms.URLInput(attrs={'class': 'form-control'}),
            'github_profile': forms.URLInput(attrs={'class': 'form-control'}),
        }


class SettingsForm(forms.ModelForm):
    """Basic settings form to edit name and theme."""
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    theme = forms.ChoiceField(choices=UserProfile.THEME_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = UserProfile
        fields = ['theme']

class UserAchievementForm(forms.ModelForm):
    """Form for adding user achievements and awards."""
    
    class Meta:
        model = UserAchievement
        fields = ['title', 'type', 'organization', 'date_received', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Achievement or award title'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Organization that granted the achievement'
            }),
            'date_received': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Month/Year or date received'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description of the achievement and its significance',
                'rows': 3
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            })
        }

class UserCertificationForm(forms.ModelForm):
    """Form for adding user certifications."""
    
    class Meta:
        model = UserCertification
        fields = ['name', 'issuer', 'date_earned', 'expiration_date', 'credential_id', 'credential_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Certification name'
            }),
            'issuer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Organization that issued the certification'
            }),
            'date_earned': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Month/Year or date earned'
            }),
            'expiration_date': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Expiration date (if applicable)'
            }),
            'credential_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Certification number or ID (optional)'
            }),
            'credential_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL to verify the certification (optional)'
            })
        }

class UserEducationForm(forms.ModelForm):
    """Form for adding and editing user education."""
    
    class Meta:
        model = UserEducation
        fields = ['institution', 'degree', 'field_of_study', 'graduation_date', 'gpa', 'additional_info']
        widgets = {
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'School, college, or university name'
            }),
            'degree': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Degree or certificate earned'
            }),
            'field_of_study': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Major or field of study'
            }),
            'graduation_date': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year or date of graduation'
            }),
            'gpa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'GPA or academic performance metric'
            }),
            'additional_info': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional information, honors, activities, etc.',
                'rows': 3
            })
        }
