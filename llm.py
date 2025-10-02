# ============================================================================
# llm.py - LLM integration with OpenRouter API (no OpenAI dependency)
# ============================================================================
from typing import List, Dict, Callable, TypeVar, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import httpx
import json
import numpy as np
import hashlib
import time
from functools import lru_cache

T = TypeVar('T')


class OpenRouterClient:
    """Custom HTTP client for OpenRouter API (replaces OpenAI client)"""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=60.0)

    def chat(self):
        """Return self to mimic OpenAI client structure"""
        return self

    def completions(self):
        """Return self to mimic OpenAI client structure"""
        return self

    def create(self, **kwargs):
        """Make a chat completion request to OpenRouter"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "Timepoint-Daedalus"  # Optional
        }

        data = {
            "model": kwargs.get("model"),
            "messages": kwargs.get("messages", []),
            "temperature": kwargs.get("temperature", 1.0),
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": kwargs.get("response_format"),
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        try:
            response = self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()


class ModelManager:
    """Manages available Llama models from OpenRouter with caching"""

    def __init__(self, api_key: str, cache_ttl_hours: int = 24):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._models_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None

    def get_llama_models(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all available Llama models from OpenRouter.
        Uses caching to avoid excessive API calls.
        """
        now = datetime.now()

        # Check if we have valid cached data
        if (not force_refresh and
            self._models_cache is not None and
            self._cache_timestamp is not None and
            now - self._cache_timestamp < self.cache_ttl):
            return self._models_cache

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Create a temporary httpx client for this request
            with httpx.Client(timeout=10.0) as http_client:
                response = http_client.get(f"{self.base_url}/models", headers=headers)
                response.raise_for_status()

            models_data = response.json()
            all_models = models_data.get("data", [])

            # Filter for Llama models (exclude non-Llama models that might have "llama" in name)
            llama_models = []
            for model in all_models:
                model_id = model.get("id", "").lower()
                # More specific filtering for actual Llama models
                is_llama = (
                    "meta-llama/llama" in model_id or
                    "meta-llama/llama3" in model_id or
                    "meta-llama/llama-3" in model_id or
                    ("llama" in model_id and not any(skip in model_id for skip in [
                        "deepseek", "distill", "guard", "codellama", "llama-cpp"
                    ]))
                )
                if is_llama:
                    llama_models.append({
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "description": model.get("description", ""),
                        "context_length": model.get("context_length", 0),
                        "pricing": model.get("pricing", {})
                    })

            # Sort by context length (higher first) and then by name
            llama_models.sort(key=lambda x: (-x["context_length"], x["name"]))

            # Cache the results
            self._models_cache = llama_models
            self._cache_timestamp = now

            print(f"📋 Fetched {len(llama_models)} Llama models from OpenRouter")
            return llama_models

        except Exception as e:
            print(f"⚠️ Failed to fetch models from OpenRouter: {e}")
            # Return cached data if available, otherwise return empty list
            if self._models_cache is not None:
                print("📋 Using cached model data")
                return self._models_cache
            return []

    def get_default_model(self) -> str:
        """Get the default Llama model (70B if available, otherwise largest context model)"""
        models = self.get_llama_models()
        if not models:
            return "meta-llama/llama-3.1-8b-instruct"  # Fallback

        # Look for 70B model first
        for model in models:
            if "70b" in model["id"].lower() and "instruct" in model["id"].lower():
                return model["id"]

        # Look for any 70B model
        for model in models:
            if "70b" in model["id"].lower():
                return model["id"]

        # Otherwise return the model with highest context length
        models.sort(key=lambda x: x["context_length"], reverse=True)
        return models[0]["id"] if models else "meta-llama/llama-3.1-8b-instruct"

    def is_valid_model(self, model_id: str) -> bool:
        """Check if a model ID is a valid Llama model"""
        models = self.get_llama_models()
        return any(model["id"] == model_id for model in models)

    def list_models_formatted(self) -> str:
        """Return a formatted string of available Llama models"""
        models = self.get_llama_models()
        if not models:
            return "No Llama models available"

        lines = ["🦙 Available Llama Models:"]
        for i, model in enumerate(models[:10], 1):  # Show top 10
            context_mb = model["context_length"] // 1024 if model["context_length"] else 0
            lines.append(f"{i}. {model['id']} ({context_mb}K context)")

        if len(models) > 10:
            lines.append(f"... and {len(models) - 10} more models")

        return "\n".join(lines)

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
    """Unified LLM client with cost tracking, dry-run support, and model selection"""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", dry_run: bool = False, default_model: Optional[str] = None, model_cache_ttl_hours: int = 24):
        self.dry_run = dry_run
        self.token_count = 0
        self.cost = 0.0
        self.api_key = api_key
        self.base_url = base_url

        # Initialize model manager for Llama models
        self.model_manager = ModelManager(api_key, model_cache_ttl_hours)

        # Set default model (prefer Llama 70B, fallback to first available Llama)
        if default_model:
            self.default_model = default_model
        else:
            self.default_model = self.model_manager.get_default_model()

        print(f"🦙 Using LLM model: {self.default_model}")
        if not dry_run:
            print(f"📋 Available Llama models: {len(self.model_manager.get_llama_models())} cached")

        if not dry_run:
            self.client = OpenRouterClient(api_key=api_key, base_url=base_url)
        else:
            self.client = None
    
    def populate_entity(self, entity_schema: Dict, context: Dict, previous_knowledge: List[str] = None, model: Optional[str] = None) -> EntityPopulation:
        """Populate entity with structured output"""
        if self.dry_run:
            return self._mock_entity_population(entity_schema, previous_knowledge)

        # Include previous knowledge in the prompt for causal evolution
        previous_context = ""
        if previous_knowledge:
            previous_context = f"\nPrevious knowledge state: {previous_knowledge}\nGenerate how this entity has evolved - what new information they've acquired and how their state has changed."

        prompt = f"""Generate entity information for {entity_schema['entity_id']}.
Context: {context}{previous_context}

Return a JSON object with these exact fields:
- knowledge_state: array of strings (3-8 knowledge items)
- energy_budget: number between 0-100
- personality_traits: array of exactly 5 floats between -1 and 1
- temporal_awareness: string describing time perception
- confidence: number between 0 and 1

Return only valid JSON, no other text."""

        # Use provided model or default to Llama model
        selected_model = model or self.default_model

        def _api_call():
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            # Extract content from response
            content = response["choices"][0]["message"]["content"]
            # Parse JSON manually
            try:
                data = json.loads(content.strip())
                return EntityPopulation(**data)
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response as JSON: {e}. Content: {content}")

        response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

        self.token_count += 1000  # Estimate
        self.cost += 0.01  # Estimate
        return response
    
    def validate_consistency(self, entities: List[Dict], timepoint: datetime, model: Optional[str] = None) -> ValidationResult:
        """Validate temporal consistency"""
        if self.dry_run:
            return ValidationResult(is_valid=True, violations=[], confidence=1.0, reasoning="Dry run mock")

        prompt = f"""Validate temporal consistency of entities at {timepoint}.
Entities: {entities}
Check for: anachronisms, biological impossibilities, knowledge contradictions.

Return a JSON object with these exact fields:
- is_valid: boolean (true if no issues found)
- violations: array of strings (list of problems found)
- confidence: number between 0 and 1 (confidence in validation)
- reasoning: string explaining the validation result

Return only valid JSON, no other text."""

        # Use provided model or default to Llama model
        selected_model = model or self.default_model

        def _api_call():
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800
            )
            # Extract content from response
            content = response["choices"][0]["message"]["content"]
            # Parse JSON manually
            try:
                data = json.loads(content.strip())
                return ValidationResult(**data)
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response as JSON: {e}. Content: {content}")

        response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

        self.token_count += 800
        self.cost += 0.008
        return response

    def score_relevance(self, query: str, knowledge_item: str, model: Optional[str] = None) -> float:
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

        # Use provided model or default to Llama model
        selected_model = model or self.default_model

        def _api_call():
            # For relevance scoring, we want raw text response, not structured
            response = self.client.chat.completions.create(
                model=selected_model,
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

