"""
Skills extraction and analysis module.
This package provides tools for extracting skills from text and analyzing them.
"""

# Don't import modules here to avoid circular imports
# Applications should import specific modules as needed

# Define what should be exported by default
__all__ = ['SkillExtractor', 'ResumeParser']

# Note: SkillAnalyzer imported conditionally to avoid circular imports
# Access via models.skills.skill_analyzer.SkillAnalyzer 