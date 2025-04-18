"""
Skills extraction and analysis module.
This package provides tools for extracting skills from text and analyzing them.
"""

# Import core components
from .skill_extractor import SkillExtractor
from .resume_parser import ResumeParser

# Expose public API
__all__ = ['SkillExtractor', 'ResumeParser']

# Note: SkillAnalyzer imported conditionally to avoid circular imports
# Access via models.skills.skill_analyzer.SkillAnalyzer 