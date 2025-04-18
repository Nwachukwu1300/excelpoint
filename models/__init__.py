"""
Machine learning models for CareerNexus.
This package contains various models for data analysis and prediction.
"""

# Import all submodules
from . import skills

# Expose commonly used classes
from .skills import SkillExtractor, SkillAnalyzer

__all__ = ['skills', 'SkillExtractor', 'SkillAnalyzer'] 