# Backstory Verification Module

A comprehensive system for verifying if a hypothesized backstory aligns with a given narrative text using AI-powered analysis.

## Features

- **Binary Consistency Judgment**: Returns 1 (consistent) or 0 (contradictory)
- **Comprehensive Evidence Rationale**: Detailed analysis with:
  - Excerpts from primary text
  - Explicit linkage to backstory claims
  - Analysis of constraints and refutations
- **Knowledge Graph Construction**: Extracts events, characters, constraints, and causal relationships
- **Hybrid Retrieval**: Vector search + metadata filtering for evidence gathering
- **Multi-stage Verification**: Rule-based constraints + LLM reasoning

## Installation
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`
2. Add your Groq API key:
````
   GROQ_API_KEY=your_key_here