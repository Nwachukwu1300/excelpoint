from django import forms

class ResumeUploadForm(forms.Form):
    """Form for uploading resumes."""
    
    resume = forms.FileField(
        label="Upload Resume",
        help_text="Upload your resume (PDF, DOCX, or TXT file)",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def clean_resume(self):
        """Validate the uploaded file."""
        resume = self.cleaned_data.get('resume')
        
        if resume:
            file_extension = resume.name.split('.')[-1].lower()
            
            if file_extension not in ['pdf', 'docx', 'txt']:
                raise forms.ValidationError(
                    "Invalid file format. Please upload a PDF, DOCX, or TXT file."
                )
                
            # Check file size (max 5 MB)
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "File size exceeds 5 MB. Please upload a smaller file."
                )
                
        return resume

class SkillExtractionForm(forms.Form):
    """Form for text-based skill extraction."""
    
    text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        label="Text to analyze",
        help_text="Enter text from which to extract skills"
    )
    
    min_confidence = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.7,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05'}),
        label="Minimum confidence",
        help_text="Minimum confidence threshold for extracted skills (0.0-1.0)"
    )

class BasicSkillExtractionForm(forms.Form):
    """Form for basic text-based skill extraction (no spaCy required)."""
    
    text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        label="Text to analyze",
        help_text="Enter text from which to extract skills (using pattern-based extraction)"
    )
    
    min_confidence = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.7,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05'}),
        label="Minimum confidence",
        help_text="Minimum confidence threshold for extracted skills (0.0-1.0)"
    ) 