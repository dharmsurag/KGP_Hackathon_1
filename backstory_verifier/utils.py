"""
Utility functions for the backstory verifier
"""

import re
import json
from typing import Dict, List, Optional


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON from text that might contain markdown or extra content
    
    Args:
        text: Text potentially containing JSON
    
    Returns:
        Parsed JSON object or None
    """
    # Try to find JSON in markdown code block
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    
    # Remove any remaining markdown
    text = text.replace('```', '').strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object/array in text
        json_pattern = r'(\{.*\}|\[.*\])'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return None


def format_evidence_item(evidence: Dict, index: int) -> str:
    """
    Format a single evidence item for output
    
    Args:
        evidence: Evidence dictionary
        index: Index number
    
    Returns:
        Formatted evidence string
    """
    return f"""
Evidence {index}:
  Source: {evidence.get('chunk_id', 'Unknown')}
  Relevance Score: {evidence.get('score', 0):.2f}
  Text Excerpt: "{evidence.get('text', '')[:200]}..."
  Position in Narrative: {evidence.get('metadata', {}).get('position', 0):.1%}
"""


def format_claim_analysis(claim: Dict, result: Dict, index: int) -> str:
    """
    Format claim analysis for comprehensive rationale
    
    Args:
        claim: Original claim
        result: Verification result
        index: Claim index
    
    Returns:
        Formatted analysis string
    """
    verdict_symbol = {
        'SUPPORT': '✓ SUPPORTS',
        'CONTRADICT': '✗ CONTRADICTS',
        'REJECT': '✗ CONTRADICTS',
        'INSUFFICIENT': '? INSUFFICIENT'
    }.get(result.get('verdict'), '? UNKNOWN')
    
    analysis = f"""
{'='*70}
CLAIM {index}: {claim.get('description')}
{'='*70}

Type: {claim.get('type')}
Subject: {claim.get('subject', 'N/A')}
Temporal Context: {claim.get('temporal', 'Unspecified')}

VERIFICATION RESULT: {verdict_symbol}
Confidence: {result.get('confidence', 0):.1%}

ANALYSIS:
{result.get('reasoning', 'No reasoning provided')}
"""
    
    # Add key evidence
    if result.get('key_evidence'):
        analysis += "\n\nKEY SUPPORTING/CONTRADICTING EVIDENCE:\n"
        for i, evidence in enumerate(result.get('key_evidence', []), 1):
            analysis += f"  {i}. {evidence}\n"
    
    # Add concerns
    if result.get('concerns'):
        analysis += "\n\nCONCERNS:\n"
        for concern in result.get('concerns', []):
            analysis += f"  • {concern}\n"
    
    # Add evidence excerpts
    if result.get('evidence_used'):
        analysis += "\n\nEVIDENCE EXCERPTS FROM PRIMARY TEXT:\n"
        for i, evidence in enumerate(result.get('evidence_used', [])[:3], 1):
            analysis += format_evidence_item(evidence, i)
    
    return analysis


def calculate_consistency_score(results: List[Dict]) -> float:
    """
    Calculate overall consistency score from individual claim results
    
    Args:
        results: List of claim verification results
    
    Returns:
        Consistency score between 0 and 1
    """
    if not results:
        return 0.0
    
    supported = len([r for r in results if r.get('verdict') == 'SUPPORT'])
    total = len(results)
    
    return supported / total


def determine_consistency_judgment(
    score: float,
    threshold: float,
    overall_coherent: bool
) -> int:
    """
    Determine binary consistency judgment
    
    Args:
        score: Consistency score (0-1)
        threshold: Threshold for consistency
        overall_coherent: Whether claims are internally coherent
    
    Returns:
        1 for consistent, 0 for contradictory
    """
    # Must meet both criteria:
    # 1. Enough claims supported (>= threshold)
    # 2. Claims are internally coherent
    return 1 if (score >= threshold and overall_coherent) else 0