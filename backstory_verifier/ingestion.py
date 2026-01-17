"""
Narrative ingestion and knowledge extraction
"""

import json
import re
from typing import List, Dict
import tiktoken
import chromadb
from groq import Groq

from .config import get_config
from .utils import extract_json_from_text


class NarrativeIngestor:
    """Handles narrative text ingestion and knowledge extraction"""
    
    def __init__(self):
        self.config = get_config()
        self.client = Groq(api_key=self.config.groq_api_key)
        self.chroma_client = chromadb.Client()
    
    def chunk_text(self, text: str) -> List[Dict]:
        """Chunk text with overlap at sentence boundaries"""
        enc = tiktoken.get_encoding("cl100k_base")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_id = 0
        total_tokens = len(enc.encode(text))
        
        for sentence in sentences:
            sent_tokens = len(enc.encode(sentence))
            
            if current_tokens + sent_tokens > self.config.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'id': f'chunk_{chunk_id}',
                    'text': chunk_text,
                    'token_count': current_tokens,
                    'position': len(enc.encode(' '.join([c['text'] for c in chunks]))) / total_tokens if total_tokens > 0 else 0
                })
                
                # Keep overlap
                overlap_sentences = []
                overlap_tokens = 0
                for s in reversed(current_chunk):
                    s_tokens = len(enc.encode(s))
                    if overlap_tokens + s_tokens <= self.config.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
                chunk_id += 1
            
            current_chunk.append(sentence)
            current_tokens += sent_tokens
        
        if current_chunk:
            chunks.append({
                'id': f'chunk_{chunk_id}',
                'text': ' '.join(current_chunk),
                'token_count': current_tokens,
                'position': 1.0
            })
        
        return chunks
    
    def extract_from_chunk(self, chunk_text: str, chunk_id: str) -> Dict:
        """Extract structured information from chunk"""
        prompt = f"""Extract key information from this narrative chunk. Output ONLY valid JSON.

{chunk_text}

Structure:
{{
  "events": [{{"id": "evt_X", "description": "...", "participants": [...], "timestamp_hint": "..."}}],
  "characters": [{{"name": "...", "state_changes": [...], "knowledge_gained": [...]}}],
  "constraints": [{{"type": "world_rule/character_fact/location_property", "description": "...", "scope": "..."}}],
  "causal_relations": [{{"cause": "...", "effect": "...", "confidence": "high/medium/low"}}],
  "temporal_markers": ["..."]
}}

Extract only what is explicit or strongly implied."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You extract information and output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.extraction_temperature,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            extracted = extract_json_from_text(content)
            
            if extracted:
                extracted['chunk_id'] = chunk_id
                return extracted
            
        except Exception as e:
            print(f"Extraction error for {chunk_id}: {e}")
        
        return {
            'chunk_id': chunk_id,
            'events': [],
            'characters': [],
            'constraints': [],
            'causal_relations': [],
            'temporal_markers': []
        }
    
    def build_knowledge_graph(self, extractions: List[Dict]) -> Dict:
        """Build knowledge graph from extractions"""
        graph = {
            'events': {},
            'characters': {},
            'constraints': [],
            'causal_links': []
        }
        
        for extraction in extractions:
            chunk_id = extraction.get('chunk_id', 'unknown')
            
            for event in extraction.get('events', []):
                event_id = event.get('id', f"evt_{len(graph['events'])}")
                graph['events'][event_id] = {**event, 'chunk_id': chunk_id}
            
            for char in extraction.get('characters', []):
                char_name = char.get('name', 'Unknown')
                if char_name not in graph['characters']:
                    graph['characters'][char_name] = {
                        'name': char_name,
                        'states': [],
                        'knowledge': [],
                        'chunks': []
                    }
                graph['characters'][char_name]['states'].extend(char.get('state_changes', []))
                graph['characters'][char_name]['knowledge'].extend(char.get('knowledge_gained', []))
                if chunk_id not in graph['characters'][char_name]['chunks']:
                    graph['characters'][char_name]['chunks'].append(chunk_id)
            
            for constraint in extraction.get('constraints', []):
                graph['constraints'].append({**constraint, 'chunk_id': chunk_id})
            
            for link in extraction.get('causal_relations', []):
                graph['causal_links'].append({**link, 'chunk_id': chunk_id})
        
        return graph
    
    def create_vector_index(self, chunks: List[Dict], extractions: List[Dict]) -> chromadb.Collection:
        """Create vector index"""
        collection_name = f"narrative_{hash(chunks[0]['text']) % 100000}"
        
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            self.chroma_client.delete_collection(name=collection_name)
        except:
            pass
        
        collection = self.chroma_client.create_collection(name=collection_name)
        
        documents = []
        ids = []
        metadatas = []
        
        for chunk, extraction in zip(chunks, extractions):
            documents.append(chunk['text'])
            ids.append(chunk['id'])
            
            events = extraction.get('events', [])
            characters = extraction.get('characters', [])
            
            metadatas.append({
                'position': float(chunk.get('position', 0)),
                'token_count': int(chunk.get('token_count', 0)),
                'has_constraints': len(extraction.get('constraints', [])) > 0,
                'events': json.dumps([e.get('id', '') for e in events]),
                'characters': json.dumps([c.get('name', '') for c in characters])
            })
        
        collection.add(documents=documents, ids=ids, metadatas=metadatas)
        return collection
    
    def generate_summary(self, graph: Dict, chunks: List[Dict]) -> str:
        """Generate narrative summary"""
        narrative_sample = "\n\n".join([c['text'] for c in chunks[:3]])
        
        prompt = f"""Create a concise summary (max 500 words) covering:
1. World/setting rules and constraints
2. Main characters and their traits
3. Plot skeleton and major events
4. Key established facts

NARRATIVE:
{narrative_sample}

INFO: {len(graph['events'])} events, {len(graph['characters'])} characters, {len(graph['constraints'])} constraints"""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You create precise narrative summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except:
            return "Summary generation failed."
    
    def ingest(self, text: str) -> Dict:
        """Main ingestion pipeline"""
        chunks = self.chunk_text(text)
        
        extractions = []
        for chunk in chunks:
            extracted = self.extract_from_chunk(chunk['text'], chunk['id'])
            extractions.append(extracted)
        
        graph = self.build_knowledge_graph(extractions)
        print("✓ Knowledge graph constructed")
        print(graph)
        collection = self.create_vector_index(chunks, extractions)
        summary = self.generate_summary(graph, chunks)
        print("✓ Narrative summary generated")
        print(summary)
        return {
            'chunks': chunks,
            'extractions': extractions,
            'graph': graph,
            'collection': collection,
            'global_summary': summary
        }