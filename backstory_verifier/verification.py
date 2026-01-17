"""
Backstory verification logic
"""

import json
from typing import List, Dict
from groq import Groq

from .config import get_config
from .utils import extract_json_from_text, calculate_consistency_score


class BackstoryVerificationEngine:
    """Handles backstory claim verification"""
    
    def __init__(self):
        self.config = get_config()
        self.client = Groq(api_key=self.config.groq_api_key)
    
    def decompose_backstory(self, backstory: str) -> List[Dict]:
        """Decompose backstory into atomic claims"""
        prompt = f"""Decompose this backstory into atomic, verifiable claims. Output ONLY JSON.

{backstory}

Structure:
[
  {{
    "id": "claim_1",
    "type": "character_knowledge/character_state/world_rule/event/causal_link",
    "subject": "main entity",
    "description": "specific testable claim",
    "temporal": "past/before_narrative/during_narrative",
    "entities": ["..."]
  }}
]"""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You decompose claims and output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            claims = extract_json_from_text(content)
            return claims if claims else []
            
        except Exception as e:
            print(f"Decomposition error: {e}")
            return []
    
    def retrieve_evidence(self, claim: Dict, collection, graph: Dict) -> List[Dict]:
        """Retrieve evidence for claim"""
        try:
            results = collection.query(
                query_texts=[claim['description']],
                n_results=self.config.top_k_evidence * 2
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            evidence_pieces = []
            
            for i, doc_id in enumerate(results['ids'][0]):
                chunk_text = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i] if results['distances'] else 1.0
                
                score = 1.0 / (1.0 + distance)
                
                try:
                    chunk_characters = json.loads(metadata.get('characters', '[]'))
                    if claim.get('subject') in chunk_characters:
                        score *= 1.5
                except:
                    pass
                
                evidence_pieces.append({
                    'chunk_id': doc_id,
                    'text': chunk_text,
                    'score': score,
                    'metadata': metadata
                })
            
            evidence_pieces.sort(key=lambda x: x['score'], reverse=True)
            return evidence_pieces[:self.config.top_k_evidence]
            
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []
    
    def check_constraints(self, claim: Dict, graph: Dict) -> List[str]:
        """Check hard constraints"""
        violations = []
        
        for constraint in graph.get('constraints', []):
            constraint_desc = constraint.get('description', '').lower()
            claim_desc = claim.get('description', '').lower()
            
            if 'dead' in constraint_desc or 'died' in constraint_desc:
                subject = claim.get('subject', '')
                if subject and subject.lower() in constraint_desc:
                    if claim.get('temporal') in ['during_narrative', 'after']:
                        violations.append(f"Contradicts: {constraint['description']}")
            
            if 'never' in constraint_desc:
                if claim.get('subject', '').lower() in constraint_desc:
                    violations.append(f"May contradict: {constraint['description']}")
        
        return violations
    
    def verify_claim(self, claim: Dict, evidence: List[Dict], graph: Dict, summary: str) -> Dict:
        """Verify single claim with LLM"""
        evidence_text = "\n\n".join([
            f"EVIDENCE {i+1} (score: {e['score']:.2f}):\n{e['text']}"
            for i, e in enumerate(evidence)
        ]) if evidence else "[No evidence found]"
        
        constraint_text = "\n".join([
            f"- {c.get('description', 'N/A')}"
            for c in graph.get('constraints', [])[:10]
        ])
        
        prompt = f"""Verify if this backstory claim aligns with the narrative. Be rigorous.

CLAIM:
Type: {claim['type']}
Subject: {claim.get('subject', 'N/A')}
Description: {claim['description']}
Temporal: {claim.get('temporal', 'unspecified')}

NARRATIVE CONTEXT:
{summary[:800]}

EVIDENCE:
{evidence_text}

CONSTRAINTS:
{constraint_text}

Check: temporal consistency, causal plausibility, character consistency, world rules.

Output ONLY JSON:
{{
  "verdict": "SUPPORT/CONTRADICT/INSUFFICIENT",
  "confidence": 0.0-1.0,
  "reasoning": "step-by-step analysis",
  "key_evidence": ["quotes"],
  "concerns": ["issues"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You verify claims rigorously. Output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.verification_temperature,
                max_tokens=1200
            )
            
            content = response.choices[0].message.content.strip()
            result = extract_json_from_text(content)
            
            if result:
                result['claim_id'] = claim['id']
                result['claim'] = claim
                result['evidence_used'] = evidence
                return result
                
        except Exception as e:
            print(f"Verification error: {e}")
        
        return {
            'claim_id': claim['id'],
            'claim': claim,
            'verdict': 'INSUFFICIENT',
            'confidence': 0.0,
            'reasoning': 'Verification failed',
            'key_evidence': [],
            'concerns': ['System error'],
            'evidence_used': evidence
        }
    
    def assess_coherence(self, results: List[Dict]) -> Dict:
        """Assess overall coherence"""
        supported = [r for r in results if r['verdict'] == 'SUPPORT']
        
        if len(supported) == 0:
            return {'coherent': False, 'confidence': 1.0, 'reasoning': 'No claims supported', 'issues': []}
        
        if len(supported) < len(results) * 0.3:
            return {'coherent': False, 'confidence': 0.8, 'reasoning': 'Low support rate', 'issues': []}
        
        claims_text = "\n".join([
            f"{i+1}. {r['claim']['description']}"
            for i, r in enumerate(supported)
        ])
        
        prompt = f"""Check if these verified claims are internally coherent.

CLAIMS:
{claims_text}

Do they contradict each other? Have logical/temporal issues?

Output ONLY JSON:
{{
  "coherent": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "analysis",
  "issues": ["problems or []"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You check internal consistency. Output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            result = extract_json_from_text(content)
            return result if result else {'coherent': False, 'confidence': 0.5, 'reasoning': 'Check failed', 'issues': []}
            
        except:
            return {'coherent': len(supported) > len(results) * 0.5, 'confidence': 0.5, 'reasoning': 'Heuristic', 'issues': []}
    
    def verify(self, backstory: str, narrative_data: Dict) -> Dict:
        """Main verification pipeline"""
        claims = self.decompose_backstory(backstory)
        
        if not claims:
            return {
                'claims': [],
                'results': [],
                'coherence': {'coherent': False},
                'consistency_score': 0.0
            }
        
        results = []
        for claim in claims:
            violations = self.check_constraints(claim, narrative_data['graph'])
            
            if violations:
                result = {
                    'claim_id': claim['id'],
                    'claim': claim,
                    'verdict': 'REJECT',
                    'confidence': 1.0,
                    'reasoning': 'Hard constraint violation',
                    'key_evidence': [],
                    'concerns': violations,
                    'evidence_used': []
                }
            else:
                evidence = self.retrieve_evidence(claim, narrative_data['collection'], narrative_data['graph'])
                result = self.verify_claim(claim, evidence, narrative_data['graph'], narrative_data['global_summary'])
            
            results.append(result)
        
        coherence = self.assess_coherence(results)
        score = calculate_consistency_score(results)
        
        return {
            'claims': claims,
            'results': results,
            'coherence': coherence,
            'consistency_score': score
        }