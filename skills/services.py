from django.db.models import Q
from .models import Skill, CareerRole, RoleSkill, Course, CourseSkill

class SkillGapAnalyzer:
    """
    Service class for analyzing skill gaps and recommending courses.
    """
    
    def analyze_skill_gap(self, user, role_id):
        """
        Analyze the skill gap between a user's skills and a target role.
        
        Args:
            user: Django User object
            role_id: ID of the CareerRole to analyze against
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get the target role
            role = CareerRole.objects.get(id=role_id)
            
            # Get the user's skills (both direct and M2M)
            user_direct_skills = set(s.name.lower() for s in user.user_skills_direct.all())
            user_m2m_skills = set(s.name.lower() for s in user.skills.all())
            user_skills = user_direct_skills.union(user_m2m_skills)
            
            # Get skills required for the role
            role_skills = RoleSkill.objects.filter(role=role)
            
            # Separate skills by importance
            essential_skills = {s.skill_name.lower(): s for s in role_skills.filter(importance='essential')}
            important_skills = {s.skill_name.lower(): s for s in role_skills.filter(importance='important')}
            nice_to_have_skills = {s.skill_name.lower(): s for s in role_skills.filter(importance='nice_to_have')}
            
            # Find skill gaps
            missing_essential = [s for s in essential_skills.keys() if s not in user_skills]
            missing_important = [s for s in important_skills.keys() if s not in user_skills]
            missing_nice_to_have = [s for s in nice_to_have_skills.keys() if s not in user_skills]
            
            # Calculate match percentage
            total_skills = len(essential_skills) + len(important_skills) + len(nice_to_have_skills)
            if total_skills == 0:
                match_percentage = 0
            else:
                # Weighted calculation: essential skills count more
                essential_weight = 0.6
                important_weight = 0.3
                nice_to_have_weight = 0.1
                
                essential_match = 0 if not essential_skills else (len(essential_skills) - len(missing_essential)) / len(essential_skills)
                important_match = 0 if not important_skills else (len(important_skills) - len(missing_important)) / len(important_skills)
                nice_to_have_match = 0 if not nice_to_have_skills else (len(nice_to_have_skills) - len(missing_nice_to_have)) / len(nice_to_have_skills)
                
                match_percentage = (
                    (essential_match * essential_weight) +
                    (important_match * important_weight) +
                    (nice_to_have_match * nice_to_have_weight)
                ) * 100
            
            # Format the result
            return {
                'success': True,
                'role': {
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'category': role.category
                },
                'user_skills': list(user_skills),
                'match_percentage': round(match_percentage, 1),
                'missing_skills': {
                    'essential': missing_essential,
                    'important': missing_important,
                    'nice_to_have': missing_nice_to_have
                },
                'total_missing': len(missing_essential) + len(missing_important) + len(missing_nice_to_have)
            }
        except CareerRole.DoesNotExist:
            return {
                'success': False,
                'error': f"Career role with ID {role_id} not found"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def recommend_courses(self, missing_skills, max_courses=5):
        """
        Recommend courses based on missing skills.
        
        Args:
            missing_skills: List of skill names that the user is missing
            max_courses: Maximum number of courses to recommend per skill
            
        Returns:
            Dictionary with course recommendations
        """
        recommendations = {}
        
        # Convert to lowercase for case-insensitive matching
        missing_skills_lower = [s.lower() for s in missing_skills]
        
        # Find courses that teach these skills
        for skill in missing_skills_lower:
            # Find CourseSkill mappings for this skill
            course_skills = CourseSkill.objects.filter(
                skill_name__iexact=skill
            ).select_related('course')
            
            # Convert to list of course dictionaries
            courses = []
            for cs in course_skills:
                course = cs.course
                courses.append({
                    'id': course.id,
                    'title': course.title,
                    'provider': course.provider,
                    'url': course.url,
                    'description': course.description,
                    'difficulty': course.difficulty,
                    'duration': course.duration,
                    'is_free': course.is_free,
                    'proficiency_level': cs.proficiency_level
                })
            
            # Limit number of courses per skill
            recommendations[skill] = courses[:max_courses]
        
        return recommendations
        
    def get_top_recommended_roles(self, user, limit=5):
        """
        Get the top career roles that best match a user's existing skills.
        
        Args:
            user: Django User object
            limit: Maximum number of roles to recommend
            
        Returns:
            List of roles with match percentages
        """
        # Get the user's skills
        user_direct_skills = set(s.name.lower() for s in user.user_skills_direct.all())
        user_m2m_skills = set(s.name.lower() for s in user.skills.all())
        user_skills = user_direct_skills.union(user_m2m_skills)
        
        # Get all career roles
        roles = CareerRole.objects.all()
        
        # Calculate match percentage for each role
        role_matches = []
        for role in roles:
            # Get skills required for this role
            role_skills = RoleSkill.objects.filter(role=role)
            required_skills = set(s.skill_name.lower() for s in role_skills)
            
            # Calculate simple match percentage
            if not required_skills:
                continue
                
            matching_skills = required_skills.intersection(user_skills)
            match_percentage = (len(matching_skills) / len(required_skills)) * 100
            
            role_matches.append({
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'category': role.category,
                'match_percentage': round(match_percentage, 1),
                'matching_skills': list(matching_skills)
            })
        
        # Sort by match percentage in descending order
        role_matches.sort(key=lambda x: x['match_percentage'], reverse=True)
        
        return role_matches[:limit] 