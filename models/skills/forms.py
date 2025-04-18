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

class JobPostingForm(forms.Form):
    """Form for submitting job postings."""
    
    job_title = forms.CharField(
        label="Job Title",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    job_description = forms.CharField(
        label="Job Description",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Paste the full job description here...'
        })
    )
    
    company = forms.CharField(
        label="Company",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def clean_job_description(self):
        """Validate the job description."""
        job_description = self.cleaned_data.get('job_description')
        
        if job_description:
            # Check minimum length (at least 100 characters)
            if len(job_description) < 100:
                raise forms.ValidationError(
                    "Job description is too short. Please provide a more detailed description."
                )
                
        return job_description

class SkillExtractionForm(forms.Form):
    """Form for extracting skills from text."""
    
    text = forms.CharField(
        label="Text",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Enter text to extract skills from...'
        })
    )
    
    min_confidence = forms.FloatField(
        label="Minimum Confidence",
        min_value=0.0,
        max_value=1.0,
        initial=0.7,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 0.05
        })
    ) 