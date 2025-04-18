from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib import messages

from .django_integration import ResumeProcessingService
from .forms import ResumeUploadForm, JobPostingForm, SkillExtractionForm

class ResumeParserView(View):
    """View for parsing resumes and extracting skills."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the resume upload form."""
        context = {
            'resume_form': ResumeUploadForm(),
            'job_form': JobPostingForm()
        }
        return render(request, 'resume_parser.html', context)
    
    def post(self, request):
        """Process the uploaded resume."""
        resume_form = ResumeUploadForm(request.POST, request.FILES)
        
        if 'resume' in request.FILES and resume_form.is_valid():
            resume_file = request.FILES['resume']
            
            # Process the resume file
            result = self.service.process_resume_file(resume_file, save_result=True)
            
            if result['success']:
                messages.success(request, f"Successfully parsed resume: {resume_file.name}")
                
                # Store result in session for the results page
                request.session['resume_parsing_result'] = result
                
                return redirect('resume_results')
            else:
                messages.error(request, f"Error parsing resume: {result['error']}")
        
        # If we get here, there was an error
        context = {
            'resume_form': resume_form,
            'job_form': JobPostingForm()
        }
        return render(request, 'resume_parser.html', context)

class ResumeResultsView(View):
    """View for displaying resume parsing results."""
    
    def get(self, request):
        """Display the resume parsing results."""
        result = request.session.get('resume_parsing_result')
        
        if not result:
            messages.error(request, "No resume parsing results found. Please upload a resume first.")
            return redirect('resume_parser')
        
        context = {'result': result}
        return render(request, 'resume_results.html', context)

class JobSkillMatchView(View):
    """View for comparing resume skills with job posting."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the job posting form."""
        # Check if we have a resume result in the session
        if 'resume_parsing_result' not in request.session:
            messages.error(request, "Please upload a resume first.")
            return redirect('resume_parser')
            
        context = {
            'job_form': JobPostingForm()
        }
        return render(request, 'job_skill_match.html', context)
    
    def post(self, request):
        """Process job posting and compare with resume."""
        job_form = JobPostingForm(request.POST)
        
        if 'job_description' in request.POST and job_form.is_valid():
            job_description = job_form.cleaned_data['job_description']
            
            # Check if we have a resume result in the session
            if 'resume_parsing_result' not in request.session:
                messages.error(request, "Please upload a resume first.")
                return redirect('resume_parser')
            
            resume_result = request.session['resume_parsing_result']
            
            # Extract resume text from the parsing result
            if resume_result['success'] and 'data' in resume_result:
                # This assumes you have the full text in the parsing result
                # Adjust according to your actual data structure
                resume_text = resume_result.get('full_text', '')
                
                if not resume_text:
                    # Try to reconstruct from sections
                    sections = resume_result['data']
                    resume_text = ' '.join([
                        sections.get('summary', ''),
                        ' '.join(str(exp) for exp in sections.get('experience', [])),
                        ' '.join(str(edu) for edu in sections.get('education', []))
                    ])
                
                # Calculate skill match
                match_result = self.service.calculate_skill_match(resume_text, job_description)
                
                # Store match result in session
                request.session['skill_match_result'] = match_result
                
                return redirect('skill_match_results')
            
            else:
                messages.error(request, "Invalid resume data. Please upload again.")
        
        # If we get here, there was an error
        context = {'job_form': job_form}
        return render(request, 'job_skill_match.html', context)

class SkillMatchResultsView(View):
    """View for displaying skill match results."""
    
    def get(self, request):
        """Display the skill match results."""
        match_result = request.session.get('skill_match_result')
        
        if not match_result:
            messages.error(request, "No skill match results found. Please match with a job first.")
            return redirect('resume_parser')
        
        context = {'match_result': match_result}
        return render(request, 'skill_match_results.html', context)

class SkillExtractAPIView(View):
    """API view for extracting skills from text."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the skill extraction form."""
        context = {'form': SkillExtractionForm()}
        return render(request, 'skill_extract.html', context)
    
    def post(self, request):
        """Extract skills from posted text."""
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            text = request.POST.get('text', '')
            min_confidence = float(request.POST.get('min_confidence', 0.7))
            
            if not text:
                return JsonResponse({
                    'success': False,
                    'error': 'No text provided'
                })
            
            # Extract skills
            skills = self.service.extract_skills_from_text(text, min_confidence)
            
            return JsonResponse({
                'success': True,
                'skills_count': len(skills),
                'skills': skills
            })
        
        # Handle form submission for non-AJAX requests
        form = SkillExtractionForm(request.POST)
        
        if form.is_valid():
            text = form.cleaned_data['text']
            min_confidence = form.cleaned_data['min_confidence']
            
            # Extract skills
            skills = self.service.extract_skills_from_text(text, min_confidence)
            
            context = {
                'form': form,
                'skills': skills,
                'skills_count': len(skills)
            }
            return render(request, 'skill_extract.html', context)
        
        context = {'form': form}
        return render(request, 'skill_extract.html', context) 