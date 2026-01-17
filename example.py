"""
Example usage of the BackstoryVerifier module
"""

from backstory_verifier import BackstoryVerifier

# Sample narrative
narrative = """
Alice lived in a small village called Thornwood. She had never left the village 
in her entire life. The village was surrounded by a magical barrier that prevented 
anyone from leaving.

Alice learned herbalism from Master Eldrin, the village healer. She spent her days 
gathering herbs in the nearby forest.

One day, a stranger named Marcus arrived. He told Alice about a magical sword in 
the distant mountains. Alice used an amulet her mother left her to pass through 
the barrier. She traveled for seven days and found the sword.

When Alice touched the sword, it glowed with brilliant light. She now had the 
power to save her village.
"""

# Sample backstory hypothesis
backstory = """
Alice trained as a warrior in the capital city for five years before returning 
to Thornwood. Her grandmother was a powerful sorceress who taught her magic.
Alice had visited the mountains many times as a child with her father.
"""

# Create verifier
verifier = BackstoryVerifier()

# Verify backstory
result = verifier.verify(narrative, backstory)

# Print results
print(f"\nConsistency Judgment: {result['consistent']}")
print(f"(1 = Consistent, 0 = Contradictory)\n")

print(result['rationale'])

# Access detailed stats
print("\nDetailed Statistics:")
print(f"  Claims analyzed: {result['details']['claims_analyzed']}")
print(f"  Claims supported: {result['details']['claims_supported']}")
print(f"  Claims contradicted: {result['details']['claims_contradicted']}")
print(f"  Consistency score: {result['details']['consistency_score']:.1%}")