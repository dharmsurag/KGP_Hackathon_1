"""
Configuration management for the backstory verifier
Loads settings from environment variables
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class Config:
    """Configuration container for the verification system"""
    
    def __init__(self):
        # API Configuration
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment variables. "
                "Please set it in .env file or environment."
            )
        
        # Model Configuration
        self.model_name = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        
        # Chunking Configuration
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '1000'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '200'))
        
        # Retrieval Configuration
        self.top_k_evidence = int(os.getenv('TOP_K_EVIDENCE', '5'))
        
        # Verification Configuration
        self.consistency_threshold = float(os.getenv('CONSISTENCY_THRESHOLD', '0.5'))
        # If >= 50% of claims are supported, consider consistent
        
        # Temperature settings
        self.extraction_temperature = float(os.getenv('EXTRACTION_TEMP', '0.3'))
        self.verification_temperature = float(os.getenv('VERIFICATION_TEMP', '0.2'))
    
    def validate(self):
        """Validate configuration"""
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required")
        
        if self.chunk_size < 100:
            raise ValueError("CHUNK_SIZE must be at least 100")
        
        if self.consistency_threshold < 0 or self.consistency_threshold > 1:
            raise ValueError("CONSISTENCY_THRESHOLD must be between 0 and 1")
        
        return True


# Global config instance
_config = None

def get_config() -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config()
        _config.validate()
    return _config