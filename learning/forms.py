from django import forms
from .models import SavedResource

class SavedResourceForm(forms.ModelForm):
    """Form for adding and editing saved resources."""
    
    class Meta:
        model = SavedResource
        fields = ['title', 'url', 'description', 'resource_type', 'tags', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter resource title'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter resource URL'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a brief description'
            }),
            'resource_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tags separated by commas'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any personal notes'
            })
        }
    
    def clean_tags(self):
        """Clean and format tags."""
        tags = self.cleaned_data['tags']
        if tags:
            # Split by comma, strip whitespace, and remove empty tags
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            # Join back with commas
            return ', '.join(tags)
        return tags
