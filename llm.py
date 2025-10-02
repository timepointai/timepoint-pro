# ============================================================================
# llm.py - LLM integration with Instructor for structured outputs
# ============================================================================
from typing import List, Dict, Callable, TypeVar
from datetime import datetime
from pydantic import BaseModel
import instructor
from openai import OpenAI
import numpy as np
import hashlib
import time

T = TypeVar('T')

def retry_with_backoff(func: Callable[..., T], max_retries: int = 3, base_delay: float = 1.0) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        Result of the successful function call

    Raises:
        Exception: The last exception encountered if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # All retries exhausted, raise the last exception
                print(f"❌ All {max_retries + 1} attempts failed. Final error: {e}")
                raise e

            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** attempt)
            print(f"⚠️ Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay)

    # This should never be reached, but just in case
    raise last_exception

class EntityPopulation(BaseModel):
    """Structured output schema for entity population"""
    entity_id: str
    knowledge_state: List[str]
    energy_budget: float
    personality_traits: List[float]
    temporal_awareness: str
    confidence: float

class ValidationResult(BaseModel):
    """Structured validation result"""
    is_valid: bool
    violations: List[str]
    confidence: float
    reasoning: str

class LLMClient:
    """Unified LLM client with cost tracking and dry-run support"""
    
    def __init__(self, api_key: str, base_url: str, dry_run: bool = False):
        self.dry_run = dry_run
        self.token_count = 0
        self.cost = 0.0
        
        if not dry_run:
            client = OpenAI(api_key=api_key, base_url=base_url)
            self.client = instructor.from_openai(client)
        else:
            self.client = None
    
    def populate_entity(self, entity_schema: Dict, context: Dict, previous_knowledge: List[str] = None, model: str = "openai/gpt-4o-mini") -> EntityPopulation:
        """Populate entity with structured output"""
        if self.dry_run:
            return self._mock_entity_population(entity_schema, previous_knowledge)

        # Include previous knowledge in the prompt for causal evolution
        previous_context = ""
        if previous_knowledge:
            previous_context = f"\nPrevious knowledge state: {previous_knowledge}\nGenerate how this entity has evolved - what new information they've acquired and how their state has changed."

        prompt = f"""Generate entity information for {entity_schema['entity_id']}.
Context: {context}{previous_context}
Provide knowledge state, energy budget (0-100), personality traits (5 floats -1 to 1), temporal awareness, and confidence (0-1)."""
        
        def _api_call():
            return self.client.chat.completions.create(
                model=model,
                response_model=EntityPopulation,
                messages=[{"role": "user", "content": prompt}]
            )

        response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

        self.token_count += 1000  # Estimate
        self.cost += 0.01  # Estimate
        return response
    
    def validate_consistency(self, entities: List[Dict], timepoint: datetime, model: str = "openai/gpt-4o-mini") -> ValidationResult:
        """Validate temporal consistency"""
        if self.dry_run:
            return ValidationResult(is_valid=True, violations=[], confidence=1.0, reasoning="Dry run mock")
        
        prompt = f"""Validate temporal consistency of entities at {timepoint}.
Entities: {entities}
Check for: anachronisms, biological impossibilities, knowledge contradictions."""
        
        def _api_call():
            return self.client.chat.completions.create(
                model=model,
                response_model=ValidationResult,
                messages=[{"role": "user", "content": prompt}]
            )

        response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

        self.token_count += 800
        self.cost += 0.008
        return response

    def score_relevance(self, query: str, knowledge_item: str, model: str = "openai/gpt-4o-mini") -> float:
        """Score how relevant a knowledge item is to a query (0.0-1.0)"""
        if self.dry_run:
            # Simple heuristic scoring for dry run
            query_words = set(query.lower().split())
            knowledge_words = set(knowledge_item.lower().split())
            overlap = len(query_words.intersection(knowledge_words))
            total_words = len(query_words.union(knowledge_words))
            return min(1.0, overlap / max(1, total_words / 2))  # Scale to 0-1

        prompt = f"""Rate how relevant this knowledge item is to the query on a scale of 0.0 to 1.0.

Query: "{query}"
Knowledge: "{knowledge_item}"

Return only a number between 0.0 and 1.0, where:
- 1.0 = Perfectly relevant and directly answers the query
- 0.5 = Somewhat relevant but not central to the query
- 0.0 = Completely irrelevant to the query

Relevance score:"""

        def _api_call():
            # For relevance scoring, we want raw text response, not structured
            response = self.client.client.chat.completions.create(  # Use the underlying client, not instructor
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=10
            )
            return response

        try:
            response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

            score_text = response.choices[0].message.content.strip()
            # Extract numeric score
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))  # Clamp to 0-1
            except ValueError:
                # Fallback to heuristic if LLM returns non-numeric
                return self._heuristic_relevance_score(query, knowledge_item)

        except Exception as e:
            print(f"LLM relevance scoring failed after retries: {e}")
            return self._heuristic_relevance_score(query, knowledge_item)

    def _heuristic_relevance_score(self, query: str, knowledge_item: str) -> float:
        """Fallback heuristic relevance scoring"""
        query_words = set(query.lower().split())
        knowledge_words = set(knowledge_item.lower().split())
        overlap = len(query_words.intersection(knowledge_words))
        total_words = len(query_words.union(knowledge_words))
        return min(1.0, overlap / max(1, total_words / 2))
    
    def _mock_entity_population(self, entity_schema: Dict, previous_knowledge: List[str] = None) -> EntityPopulation:
        """Deterministic mock for dry-run mode"""
        import hashlib
        seed = int(hashlib.md5(entity_schema['entity_id'].encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)

        # If previous knowledge exists, generate evolved state
        if previous_knowledge:
            # Add some new knowledge while keeping some old
            existing_count = len(previous_knowledge)
            new_facts = [f"fact_{existing_count + i}" for i in range(3)]  # Add 3 new facts
            knowledge_state = previous_knowledge + new_facts
        else:
            knowledge_state = [f"fact_{i}" for i in range(5)]

        return EntityPopulation(
            entity_id=entity_schema['entity_id'],
            knowledge_state=knowledge_state,
            energy_budget=np.random.uniform(50, 100),
            personality_traits=np.random.uniform(-1, 1, 5).tolist(),
            temporal_awareness=f"Aware of events up to {entity_schema.get('timestamp', 'unknown')}",
            confidence=0.8
        )

