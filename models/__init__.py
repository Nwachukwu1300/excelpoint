"""
Machine learning models for CareerNexus.
This package contains various models for data analysis and prediction.
"""

# Import all submodules
from . import skills

# Expose commonly used classes
from .skills import SkillExtractor

# Models package

# Let Django discover the models package
# Avoid explicit imports here to prevent circular dependencies 
__all__ = [] 