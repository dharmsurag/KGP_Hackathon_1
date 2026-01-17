"""
Main interface for backstory verification
Simple API: input narrative + backstory, get consistency judgment + rationale
"""

from typing import Dict
from .ingestion import NarrativeIngestor
from .verification import BackstoryVerificationEngine
from .config import get_config
from .utils import (
    format_claim_analysis,
    determine_consistency_judgment
)


class BackstoryVerifier:
    """
    Main verification interface
    
    Usage:
        verifier = BackstoryVerifier()
        result = verifier.verify(narrative_text, backstory_text)
        
        print(f"Consistent: {result['consistent']}")
        print(result['rationale'])
    """
    
    def __init__(self):
        """Initialize verifier with configuration"""
        self.config = get_config()
        self.ingestor = NarrativeIngestor()
        self.engine = BackstoryVerificationEngine()
    
    def verify(self, narrative: str, backstory: str) -> Dict:
        """
        Verify if backstory is consistent with narrative
        
        Args:
            narrative: The primary narrative text
            backstory: The hypothesized backstory to verify
        
        Returns:
            Dictionary with:
            - consistent: Binary judgment (1=consistent, 0=contradictory)
            - rationale: Comprehensive evidence and analysis
            - details: Full verification results
        """
        
        # Step 1: Ingest narrative
        print("Ingesting narrative...")
        narrative_data = self.ingestor.ingest(narrative)
        print(f"✓ Extracted {len(narrative_data['graph']['events'])} events, "
              f"{len(narrative_data['graph']['characters'])} characters")
        
        # Step 2: Verify backstory
        print("\nVerifying backstory...")
        verification_data = self.engine.verify(backstory, narrative_data)
        print(f"✓ Analyzed {len(verification_data['claims'])} claims")
        
        # Step 3: Make consistency judgment
        consistency_score = verification_data['consistency_score']
        coherence = verification_data['coherence']
        
        consistent = determine_consistency_judgment(
            consistency_score,
            self.config.consistency_threshold,
            coherence.get('coherent', False)
        )
        
        # Step 4: Generate comprehensive rationale
        rationale = self._generate_rationale(
            verification_data,
            narrative_data,
            consistent
        )
        
        return {
            'consistent': consistent,
            'rationale': rationale,
            'details': {
                'consistency_score': consistency_score,
                'coherence_assessment': coherence,
                'claims_analyzed': len(verification_data['claims']),
                'claims_supported': len([r for r in verification_data['results'] if r['verdict'] == 'SUPPORT']),
                'claims_contradicted': len([r for r in verification_data['results'] if r['verdict'] in ['CONTRADICT', 'REJECT']]),
                'narrative_stats': {
                    'chunks': len(narrative_data['chunks']),
                    'events': len(narrative_data['graph']['events']),
                    'characters': len(narrative_data['graph']['characters']),
                    'constraints': len(narrative_data['graph']['constraints'])
                }
            }
        }
    
    def _generate_rationale(
        self,
        verification_data: Dict,
        narrative_data: Dict,
        consistent: int
    ) -> str:
        """Generate comprehensive evidence rationale"""
        
        results = verification_data['results']
        claims = verification_data['claims']
        coherence = verification_data['coherence']
        score = verification_data['consistency_score']
        
        # Header
        rationale = f"""
        {'='*80}
        COMPREHENSIVE EVIDENCE RATIONALE
        Establishing Backstory Validity Through Narrative Analysis
        {'='*80}

        CONSISTENCY JUDGMENT: {"CONSISTENT (1)" if consistent else "CONTRADICTORY (0)"}

        Overall Support Rate: {score:.1%}
        Internal Coherence: {"Yes" if coherence.get('coherent') else "No"}
        Confidence: {coherence.get('confidence', 0):.1%}

        {'='*80}
        EXECUTIVE SUMMARY
        {'='*80}

        """
        
        # Executive summary
        if consistent:
            rationale += f"""The hypothesized backstory is CONSISTENT with the narrative.
            {len([r for r in results if r['verdict'] == 'SUPPORT'])}/{len(results)} claims are supported by textual evidence,
            and the accepted claims form an internally coherent narrative foundation."""
        else:
            rationale += f"""The hypothesized backstory is CONTRADICTORY to the narrative."""

        contradicted = [r for r in results if r['verdict'] in ['CONTRADICT', 'REJECT']]
        if contradicted:
            rationale += f"""Key contradictions: {len(contradicted)} claims directly conflict with established narrative facts.""" 
        if not coherence.get('coherent'):
            rationale += f"""Additionally, even supported claims show internal inconsistencies."""
        rationale += f"""{'='*80} DETAILED CLAIM-BY-CLAIM ANALYSIS {'='*80}"""
        # Detailed analysis for each claim
        for i, (claim, result) in enumerate(zip(claims, results), 1):
            rationale += format_claim_analysis(claim, result, i)

        # Global coherence assessment
        rationale += f"""{'='*80} GLOBAL COHERENCE ASSESSMENT {'='*80}
        Internal Consistency: {"PASS" if coherence.get('coherent') else "FAIL"}
        Confidence: {coherence.get('confidence', 0):.1%}
        Analysis:
        {coherence.get('reasoning', 'No analysis available')}"""
        if coherence.get('issues'):
            rationale += "\n\nIdentified Issues:\n"
            for issue in coherence['issues']:
                rationale += f"  • {issue}\n"
        # Final conclusion
        rationale += f"""{'='*80} CONCLUSION {'='*80}
        Based on comprehensive analysis of {len(claims)} atomic claims against the primary
        narrative text, cross-referencing {len(narrative_data['chunks'])} text segments and
        {len(narrative_data['graph']['constraints'])} established constraints:
        FINAL JUDGMENT: {"CONSISTENT (1)" if consistent else "CONTRADICTORY (0)"}
        """
        if consistent:
            rationale += """The backstory is validated as consistent with the narrative. All critical claims are either explicitly supported by textual evidence or are logically compatible with
            established facts. No significant contradictions were detected."""
        else:
            rationale += """The backstory cannot be validated due to explicit contradictions with established
            narrative facts and/or internal logical inconsistencies among the backstory claims."""
        rationale += f"\n{'='*80}\n"
        return rationale
    # Convenience function for quick usage
    def verify_backstory(narrative: str, backstory: str) -> Dict:
        """
        Convenience function for one-line verification 
        Args:
            narrative: Primary narrative text
            backstory: Backstory hypothesis

        Returns:
            Verification result with consistent (0/1) and rationale
        """
        verifier = BackstoryVerifier()
        return verifier.verify(narrative, backstory)