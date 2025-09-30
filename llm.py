# ============================================================================
# llm.py - LLM integration with Instructor for structured outputs
# ============================================================================
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel
import instructor
from openai import OpenAI
import numpy as np
import hashlib

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
    
    def populate_entity(self, entity_schema: Dict, context: Dict, model: str = "openai/gpt-4o-mini") -> EntityPopulation:
        """Populate entity with structured output"""
        if self.dry_run:
            return self._mock_entity_population(entity_schema)
        
        prompt = f"""Generate entity information for {entity_schema['entity_id']}.
Context: {context}
Provide knowledge state, energy budget (0-100), personality traits (5 floats -1 to 1), temporal awareness, and confidence (0-1)."""
        
        response = self.client.chat.completions.create(
            model=model,
            response_model=EntityPopulation,
            messages=[{"role": "user", "content": prompt}]
        )
        
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
        
        response = self.client.chat.completions.create(
            model=model,
            response_model=ValidationResult,
            messages=[{"role": "user", "content": prompt}]
        )
        
        self.token_count += 800
        self.cost += 0.008
        return response
    
    def _mock_entity_population(self, entity_schema: Dict) -> EntityPopulation:
        """Deterministic mock for dry-run mode"""
        import hashlib
        seed = int(hashlib.md5(entity_schema['entity_id'].encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)
        
        return EntityPopulation(
            entity_id=entity_schema['entity_id'],
            knowledge_state=[f"fact_{i}" for i in range(5)],
            energy_budget=np.random.uniform(50, 100),
            personality_traits=np.random.uniform(-1, 1, 5).tolist(),
            temporal_awareness=f"Aware of events up to {entity_schema.get('timestamp', 'unknown')}",
            confidence=0.8
        )

