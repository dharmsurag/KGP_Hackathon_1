"""
Backstory Verification Module

A comprehensive system for verifying if a hypothesized backstory
aligns with a given narrative text.

Usage:
    from backstory_verifier import BackstoryVerifier
    
    verifier = BackstoryVerifier()
    result = verifier.verify(narrative_text, backstory_text)
    
    print(f"Consistent: {result['consistent']}")
    print(result['rationale'])
"""

from .verifier import BackstoryVerifier
from .config import Config

__version__ = "1.0.0"
__author__ = "Backstory Verification System"

__all__ = ['BackstoryVerifier', 'Config']
