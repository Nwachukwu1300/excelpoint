from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .django_integration import ResumeProcessingService
from .forms import ResumeUploadForm, SkillExtractionForm, BasicSkillExtractionForm
from .skill_extractor import SkillExtractor

class ResumeParserView(View):
    """View for parsing resumes and extracting skills."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the resume upload form."""
        # Clear any existing messages
        storage = messages.get_messages(request)
        storage.used = True
        
        context = {
            'resume_form': ResumeUploadForm(),
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
        }
        return render(request, 'resume_parser.html', context)

class ResumeResultsView(LoginRequiredMixin, View):
    """View for displaying resume parsing results."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the resume parsing results."""
        result = request.session.get('resume_parsing_result')
        
        if not result:
            messages.error(request, "No resume parsing results found. Please upload a resume first.")
            return redirect('resume_parser')
        
        context = {
            'result': result,
            'skills_added': request.session.pop('skills_added_to_profile', None)
        }
        return render(request, 'resume_results.html', context)
    
    def post(self, request):
        """Save extracted skills to user profile."""
        result = request.session.get('resume_parsing_result')
        
        if not result or not result.get('success', False):
            messages.error(request, "No valid resume parsing results found.")
            return redirect('resume_parser')
        
        # Extract skills from the resume data
        if 'data' in result and 'skills' in result['data']:
            skills_data = result['data']['skills']
            
            # Convert the categorized skills structure to a flat list of skills
            extracted_skills = []
            for category in skills_data:
                category_name = category.get('category', 'Unknown')
                for skill_name in category.get('skills', []):
                    extracted_skills.append({
                        'skill': skill_name,
                        'category': category_name,
                        'confidence': 0.8  # Default confidence
                    })
            
            # Save skills to user profile
            save_result = self.service.save_skills_to_user(
                user=request.user,
                text_or_skills=extracted_skills,
                min_confidence=0.7  # Could be configurable in the form
            )
            
            if save_result['success']:
                if save_result['total_skills'] > 0:
                    messages.success(
                        request, 
                        f"Added {save_result['total_skills']} skills to your profile: "
                        f"{', '.join(save_result['added_skills'][:5])}"
                        f"{' and more.' if len(save_result['added_skills']) > 5 else '.'}"
                    )
                else:
                    messages.info(request, "No new skills were added to your profile.")
                
                # Store the result for template display
                request.session['skills_added_to_profile'] = save_result
            else:
                messages.error(request, "Failed to add skills to your profile.")
        else:
            messages.warning(request, "No skills found in the resume parsing results.")
        
        return redirect('resume_results')

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

class BasicSkillExtractAPIView(View):
    """API view for extracting skills from text without requiring spaCy."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize with just the skill extractor, not the full resume service
        self.extractor = SkillExtractor()
    
    def get(self, request):
        """Display the basic skill extraction form."""
        context = {
            'form': BasicSkillExtractionForm(),
            'title': 'Basic Skill Extraction',
            'description': 'Extract skills using pattern-based methods (no spaCy required)'
        }
        return render(request, 'basic_skill_extract.html', context)
    
    def post(self, request):
        """Extract skills from posted text using pattern-based methods."""
        # Check if this is an AJAX request or a direct API call
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Get parameters from request
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            text = data.get('text', '')
            min_confidence = float(data.get('min_confidence', 0.7))
        else:
            text = request.POST.get('text', '')
            min_confidence = float(request.POST.get('min_confidence', 0.7))
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'No text provided'
            }, status=400)
        
        # Extract skills using the non-spaCy methods
        all_skills = self.extractor.extract_skills(text)
        
        # Filter by confidence
        filtered_skills = [skill for skill in all_skills if skill['confidence'] >= min_confidence]
        
        # Group skills by category
        skills_by_category = {}
        for skill in filtered_skills:
            category = skill.get('category', 'unknown')
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)
        
        # Prepare response data
        response_data = {
            'success': True,
            'skills_count': len(filtered_skills),
            'skills': filtered_skills,
            'skills_by_category': {
                category: [s.get('skill') for s in skills] 
                for category, skills in skills_by_category.items()
            },
            'spacy_available': self.extractor.nlp_available
        }
        
        # Return JSON for AJAX/API requests or render form with results
        if is_ajax or request.content_type == 'application/json':
            return JsonResponse(response_data)
        else:
            # For normal form submissions, render the form with results
            context = {
                'form': BasicSkillExtractionForm(request.POST),
                'title': 'Basic Skill Extraction',
                'description': 'Extract skills using pattern-based methods (no spaCy required)',
                'results': response_data,
                'skills_found': filtered_skills,
                'skills_by_category': skills_by_category
            }
            return render(request, 'basic_skill_extract.html', context) 