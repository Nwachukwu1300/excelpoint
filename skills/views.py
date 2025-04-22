from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views import View
from django.http import JsonResponse

from .models import Skill, CareerRole, RoleSkill, Course
from .forms import RoleSelectionForm
from .services import SkillGapAnalyzer

# Add imports for existing views if needed

# ... existing views ...

@login_required
def skill_gap_analysis(request):
    """View for skill gap analysis."""
    analyzer = SkillGapAnalyzer()
    
    if request.method == 'POST':
        form = RoleSelectionForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            
            # Analyze skill gap
            analysis_result = analyzer.analyze_skill_gap(request.user, role.id)
            
            if analysis_result['success']:
                # Get all missing skills in a flat list
                all_missing_skills = []
                all_missing_skills.extend(analysis_result['missing_skills']['essential'])
                all_missing_skills.extend(analysis_result['missing_skills']['important'])
                all_missing_skills.extend(analysis_result['missing_skills']['nice_to_have'])
                
                # Get course recommendations
                course_recommendations = analyzer.recommend_courses(all_missing_skills)
                
                context = {
                    'form': form,
                    'analysis_result': analysis_result,
                    'course_recommendations': course_recommendations,
                    'selected_role': role
                }
                return render(request, 'skills/skill_gap_analysis.html', context)
            else:
                messages.error(request, f"Error in analysis: {analysis_result.get('error', 'Unknown error')}")
    else:
        form = RoleSelectionForm()
        
        # Get recommended roles based on current skills
        recommended_roles = analyzer.get_top_recommended_roles(request.user)
    
    return render(request, 'skills/skill_gap_analysis.html', {
        'form': form,
        'recommended_roles': recommended_roles if 'recommended_roles' in locals() else None
    })

@login_required
def course_recommendations(request):
    """View for course recommendations."""
    if request.method == 'POST':
        # Get missing skills from POST data
        missing_skills = request.POST.getlist('missing_skills[]')
        
        if not missing_skills:
            return JsonResponse({
                'success': False,
                'error': 'No missing skills provided'
            })
        
        # Get course recommendations
        analyzer = SkillGapAnalyzer()
        recommendations = analyzer.recommend_courses(missing_skills)
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations
        })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def dream_job_path(request):
    """
    View for users to select a dream job, see skill gaps, and get a learning path.
    """
    analyzer = SkillGapAnalyzer()
    
    def process_role(role, form):
        """Helper function to process a role selection and create a learning path."""
        # Analyze skill gap
        analysis_result = analyzer.analyze_skill_gap(request.user, role.id)
        
        if not analysis_result['success']:
            messages.error(request, f"Error in analysis: {analysis_result.get('error', 'Unknown error')}")
            return None
            
        # Categorize missing skills by importance for better UX
        missing_skills = analysis_result['missing_skills']
        
        # Get course recommendations for each category of missing skills
        recommendations = {
             'essential': analyzer.recommend_courses(missing_skills['essential'], max_courses=5),
             'important': analyzer.recommend_courses(missing_skills['important'], max_courses=5),
             'nice_to_have': analyzer.recommend_courses(missing_skills['nice_to_have'], max_courses=5)
        }
        
        # Create a structured learning path
        learning_path = []
        
        # Step 1: Add essential skills courses (highest priority)
        if missing_skills['essential']:
            learning_path.append({
                'phase': 1,
                'title': 'Foundation Building - Critical Skills',
                'description': 'Master these essential skills first to build a strong foundation',
                'skills': missing_skills['essential'],
                'courses': recommendations['essential']
            })
        
        # Step 2: Add important skills courses
        if missing_skills['important']:
            learning_path.append({
                'phase': 2,
                'title': 'Skill Development - Important Competencies',
                'description': 'Develop these important skills to become more competitive',
                'skills': missing_skills['important'],
                'courses': recommendations['important']
            })
        
        # Step 3: Add nice-to-have skills courses
        if missing_skills['nice_to_have']:
            learning_path.append({
                'phase': 3,
                'title': 'Advanced Enhancement - Differentiating Skills',
                'description': 'Add these skills to stand out from other candidates',
                'skills': missing_skills['nice_to_have'],
                'courses': recommendations['nice_to_have']
            })
        
        context = {
            'form': form,
            'analysis_result': analysis_result,
            'learning_path': learning_path,
            'selected_role': role,
            'match_percentage': analysis_result['match_percentage']
        }
        return context
    
    # Check if a role is specified via URL parameter
    role_id = request.GET.get('role')
    
    if request.method == 'POST':
        form = RoleSelectionForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            context = process_role(role, form)
            if context:
                return render(request, 'skills/dream_job_path.html', context)
    else:
        # If a role is specified via URL parameter, auto-submit the form
        if role_id:
            try:
                role = CareerRole.objects.get(id=role_id)
                form = RoleSelectionForm(initial={'role': role})
                context = process_role(role, form)
                if context:
                    return render(request, 'skills/dream_job_path.html', context)
            except CareerRole.DoesNotExist:
                messages.error(request, f"Career role with ID {role_id} not found")
                form = RoleSelectionForm()
        else:
            form = RoleSelectionForm()
    
    # Get recommended roles based on current skills
    recommended_roles = analyzer.get_top_recommended_roles(request.user)
    
    return render(request, 'skills/dream_job_path.html', {
        'form': form,
        'recommended_roles': recommended_roles
    })

def list_courses(request):
    """View for listing all available courses"""
    courses = Course.objects.all().order_by('provider', 'title')
    
    return render(request, 'skills/courses_list.html', {
        'courses': courses
    })
