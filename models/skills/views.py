from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .django_integration import ResumeProcessingService
from .forms import ResumeUploadForm, SkillExtractionForm, BasicSkillExtractionForm
from .skill_extractor import SkillExtractor

# Import necessary user models
from users.models import UserEducation, UserCertification, UserAchievement

class ResumeParserView(LoginRequiredMixin, View):
    """View for parsing resumes and extracting skills."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
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
        """Redirect to confirmation page."""
        result = request.session.get('resume_parsing_result')
        
        if not result or not result.get('success', False):
            messages.error(request, "No valid resume parsing results found.")
            return redirect('resume_parser')
        
        # Check if there's data to process
        if 'data' in result:
            return redirect('resume_confirm')
        else:
            messages.warning(request, "No parsable data found in the resume results.")
            return redirect('resume_results')

class ResumeConfirmView(LoginRequiredMixin, View):
    """View for confirming resume parsed data before saving to profile."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def get(self, request):
        """Display the resume confirmation page."""
        result = request.session.get('resume_parsing_result')
        
        if not result:
            messages.error(request, "No resume parsing results found. Please upload a resume first.")
            return redirect('resume_parser')
        
        context = {
            'result': result
        }
        return render(request, 'resume_confirm.html', context)

class ResumeConfirmSaveView(LoginRequiredMixin, View):
    """View for saving confirmed resume data to user profile."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ResumeProcessingService()
    
    def post(self, request):
        """Process the edited resume data and save to user profile."""
        user = request.user
        results = {
            'success': True,
            'skills_added': 0,
            'education_added': 0,
            'certifications_added': 0,
            'achievements_added': 0,
            'errors': []
        }
        
        # Extract data from the form
        education_data = self._extract_form_data(request.POST, 'education')
        certification_data = self._extract_form_data(request.POST, 'certifications')
        achievement_data = self._extract_form_data(request.POST, 'achievements')
        
        # Save skills directly from original parsed data
        result = request.session.get('resume_parsing_result')
        if result and 'data' in result and 'skills' in result['data']:
            try:
                # Pass the skills list directly from the parsed result
                skills_data = result['data']['skills']
                
                # Log the skills data structure for debugging
                print(f"Skills data structure: {type(skills_data)}")
                print(f"Skills data content: {skills_data}")
                
                skills_result = self.service.save_skills_to_user(user, skills_data)
                results['skills_added'] = skills_result.get('total_skills', 0)
                results['added_skills'] = skills_result.get('added_skills', [])
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Error saving skills: {str(e)}")
                print(f"Error saving skills: {str(e)}")  # Log the error
        
        # Save education data
        if education_data:
            try:
                added_education = []
                for edu in education_data:
                    if 'degree' not in edu or not edu['degree']:
                        continue
                        
                    # Check if this education entry already exists
                    existing_education = UserEducation.objects.filter(
                        user=user,
                        institution__iexact=edu.get('institution', ''),
                        degree__iexact=edu.get('degree', '')
                    ).exists()
                    
                    if not existing_education:
                        # Create new education entry
                        education = UserEducation.objects.create(
                            user=user,
                            institution=edu.get('institution', ''),
                            degree=edu.get('degree', ''),
                            graduation_date=edu.get('date', ''),
                            gpa=edu.get('gpa', ''),
                            additional_info=edu.get('additional_info', '')
                        )
                        added_education.append(education)
                
                results['education_added'] = len(added_education)
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Error saving education: {str(e)}")
        
        # Save certification data
        if certification_data:
            try:
                added_certifications = []
                for cert in certification_data:
                    if 'name' not in cert or not cert['name']:
                        continue
                        
                    # Check if this certification already exists
                    existing_cert = UserCertification.objects.filter(
                        user=user,
                        name__iexact=cert.get('name', ''),
                        issuer__iexact=cert.get('issuer', '')
                    ).exists()
                    
                    if not existing_cert:
                        # Create new certification entry
                        certification = UserCertification.objects.create(
                            user=user,
                            name=cert.get('name', ''),
                            issuer=cert.get('issuer', ''),
                            date_earned=cert.get('date', ''),
                            credential_id=cert.get('credential_id', '')
                        )
                        added_certifications.append(certification)
                
                results['certifications_added'] = len(added_certifications)
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Error saving certifications: {str(e)}")
        
        # Save achievement data
        if achievement_data:
            try:
                added_achievements = []
                for achieve in achievement_data:
                    if 'title' not in achieve or not achieve['title']:
                        continue
                        
                    # Check if this achievement already exists
                    existing_achievement = UserAchievement.objects.filter(
                        user=user,
                        title__iexact=achieve.get('title', '')
                    ).exists()
                    
                    if not existing_achievement:
                        # Create new achievement entry
                        achievement = UserAchievement.objects.create(
                            user=user,
                            title=achieve.get('title', ''),
                            type=achieve.get('type', 'general'),
                            organization=achieve.get('organization', ''),
                            date_received=achieve.get('date', ''),
                            description=achieve.get('description', '')
                        )
                        added_achievements.append(achievement)
                
                results['achievements_added'] = len(added_achievements)
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Error saving achievements: {str(e)}")
        
        # Store all save results for template display
        request.session['parse_data_saved'] = results
        
        # Prepare success message parts
        message_parts = []
        
        # Add skills message if any were added
        if results.get('skills_added', 0) > 0:
            message_parts.append(f"{results['skills_added']} skills")
        
        # Add education message if any were added
        if results.get('education_added', 0) > 0:
            message_parts.append(f"{results['education_added']} education entries")
        
        # Add certifications message if any were added
        if results.get('certifications_added', 0) > 0:
            message_parts.append(f"{results['certifications_added']} certifications")
        
        # Add achievements message if any were added
        if results.get('achievements_added', 0) > 0:
            message_parts.append(f"{results['achievements_added']} achievements")
        
        # Format the full message
        if message_parts:
            # Construct the message for natural language display
            if len(message_parts) == 1:
                message = f"Added {message_parts[0]} to your profile."
            elif len(message_parts) == 2:
                message = f"Added {message_parts[0]} and {message_parts[1]} to your profile."
            else:
                message = f"Added {', '.join(message_parts[:-1])}, and {message_parts[-1]} to your profile."
            
            messages.success(request, message)
        else:
            messages.info(request, "No new information was added to your profile.")
        
        # Redirect to profile page instead of resume results
        return redirect('users:profile')
    
    def _extract_form_data(self, post_data, prefix):
        """
        Extract form data for items with the given prefix.
        
        Args:
            post_data: The POST data from the request
            prefix: The prefix for the items to extract (e.g., 'education')
            
        Returns:
            List of dictionaries with the extracted data
        """
        data = []
        
        # Get all keys that start with the prefix
        prefix_keys = [k for k in post_data.keys() if k.startswith(f"{prefix}[")]
        
        # Get the set of item indices
        item_indices = set()
        for key in prefix_keys:
            # Extract the index from keys like "education[0][degree]"
            try:
                index = key.split('[')[1].split(']')[0]
                item_indices.add(index)
            except (IndexError, ValueError):
                continue
        
        # Get the set of deleted indices
        deleted_indices = set()
        for key in post_data.keys():
            if key.startswith(f"{prefix}_delete["):
                try:
                    index = key.split('[')[1].split(']')[0]
                    deleted_indices.add(index)
                except (IndexError, ValueError):
                    continue
        
        # Process each item
        for idx in item_indices:
            if idx in deleted_indices:
                continue
                
            item_data = {}
            
            # Extract all fields for this item
            for key in prefix_keys:
                if f"{prefix}[{idx}][" in key:
                    # Extract the field name
                    field = key.split('][')[1].split(']')[0]
                    item_data[field] = post_data[key]
            
            if item_data:
                data.append(item_data)
        
        return data

class SkillExtractAPIView(LoginRequiredMixin, View):
    """View for extracting skills from text."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.extractor = SkillExtractor()
    
    def get(self, request):
        """Display the skill extraction form."""
        context = {
            'form': SkillExtractionForm()
        }
        return render(request, 'skill_extract.html', context)
    
    def post(self, request):
        """Extract skills from the provided text."""
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            text = request.POST.get('text', '')
            min_confidence = float(request.POST.get('min_confidence', 0.7))
            
            if not text:
                return JsonResponse({'error': 'No text provided'}, status=400)
            
            # Extract skills
            skills = self.extractor.extract_skills(text)
            
            return JsonResponse({
                'success': True,
                'skills': skills
            })
        
        # If not AJAX, handle form submission
        form = SkillExtractionForm(request.POST)
        
        if form.is_valid():
            text = form.cleaned_data['text']
            min_confidence = form.cleaned_data.get('min_confidence', 0.7)
            
            # Extract skills
            skills = self.extractor.extract_skills(text)
            
            context = {
                'form': form,
                'skills': skills,
                'text': text,
                'skills_count': len(skills)
            }
            return render(request, 'skill_extract.html', context)
        
        context = {'form': form}
        return render(request, 'skill_extract.html', context)

class BasicSkillExtractAPIView(LoginRequiredMixin, View):
    """Simple view for extracting skills from text."""
    
    login_url = '/users/login/'  # Redirect to login if user is not authenticated
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        """Extract skills using basic pattern matching."""
        form = BasicSkillExtractionForm(request.POST)
        
        if form.is_valid():
            text = form.cleaned_data['text']
            
            # Extract skills using basic pattern matching
            skills = self.extractor.extract_skills_basic(text)
            
            # Group skills by category
            skills_by_category = {}
            for skill in skills:
                category = skill.get('category', 'Uncategorized')
                if category not in skills_by_category:
                    skills_by_category[category] = []
                skills_by_category[category].append(skill)
            
            context = {
                'form': form,
                'text': text,
                'skills': skills,
                'skills_count': len(skills),
                'skills_by_category': skills_by_category
            }
            return render(request, 'basic_skill_extract.html', context) 