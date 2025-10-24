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

    @property
    def chat(self):
        """Return self to mimic OpenAI client structure"""
        return self

    @property
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
    entity_id: str = ""
    knowledge_state: List[str] = []
    energy_budget: float = 50.0
    personality_traits: List[float] = [0.0, 0.0, 0.0, 0.0, 0.0]
    temporal_awareness: str = "present"
    confidence: float = 0.5

class ValidationResult(BaseModel):
    """Structured validation result"""
    is_valid: bool
    violations: List[str]
    confidence: float
    reasoning: str

class LLMClient:
    """Unified LLM client with cost tracking and model selection (REAL LLM only)"""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", default_model: Optional[str] = None, model_cache_ttl_hours: int = 24):
        # VALIDATION: API key is required
        if not api_key:
            raise ValueError(
                "API key is REQUIRED. This system only supports real LLM integration. "
                "Mock/dry-run mode has been removed from this codebase."
            )

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
        print(f"📋 Available Llama models: {len(self.model_manager.get_llama_models())} cached")

        # Always create real OpenRouter client
        self.client = OpenRouterClient(api_key=api_key, base_url=base_url)
    
    def populate_entity(self, entity_schema: Dict, context: Dict, previous_knowledge: List[str] = None, model: Optional[str] = None) -> EntityPopulation:
        """Populate entity with structured output (REAL LLM only)"""
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

        # FIX: Explicitly set entity_id from schema if not in LLM response or empty
        if not response.entity_id or response.entity_id == "":
            response.entity_id = entity_schema.get('entity_id', '')

        self.token_count += 1000  # Estimate
        self.cost += 0.01  # Estimate
        return response
    
    def validate_consistency(self, entities: List[Dict], timepoint: datetime, model: Optional[str] = None) -> ValidationResult:
        """Validate temporal consistency (REAL LLM only)"""
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
        """Score how relevant a knowledge item is to a query (0.0-1.0) (REAL LLM only)"""
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

            score_text = response["choices"][0]["message"]["content"].strip()
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

    def generate_dialog(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None):
        """Generate dialog with structured output (REAL LLM only)"""
        # Use provided model or default to Llama model
        selected_model = model or self.default_model

        # Add structured output instruction to prompt
        structured_prompt = f"""{prompt}

Return a JSON object with these EXACT fields (follow this schema precisely):
- turns: array of objects, each with:
  - speaker: string (entity_id)
  - content: string (what was said - THIS FIELD MUST BE NAMED 'content' NOT 'text')
  - timestamp: string (ISO format datetime like "2023-03-15T13:00:00")
  - emotional_tone: string or null (optional inferred tone)
  - knowledge_references: array of strings (default empty array [])
  - confidence: number (0.0-1.0, default 1.0)
  - physical_state_influence: string or null (optional how physical state affected utterance)
- total_duration: integer number of seconds (e.g. 1800 for 30 minutes - MUST BE AN INTEGER NOT A STRING)
- information_exchanged: array of strings (knowledge items passed between entities)
- relationship_impacts: object mapping entity pairs to float deltas (e.g. {{"alice-bob": 0.1, "bob-charlie": -0.05}})
- atmosphere_evolution: array of objects, each with:
  - timestamp: number (seconds from start, e.g. 0.0, 30.5, 60.0)
  - atmosphere: number (0.0-1.0 representing atmosphere intensity)

CRITICAL:
- Use "content" not "text" for dialog turns
- total_duration must be an integer (seconds)
- relationship_impacts values must be floats, not objects
- atmosphere_evolution objects need timestamp and atmosphere as numbers

Return only valid JSON matching this schema exactly, no other text."""

        def _api_call():
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": structured_prompt}],
                temperature=0.7,
                max_tokens=max_tokens
            )
            # Extract content from response
            content = response["choices"][0]["message"]["content"]
            # Parse JSON manually
            try:
                from schemas import DialogData
                data = json.loads(content.strip())
                return DialogData(**data)
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response as JSON: {e}. Content: {content}")

        response = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

        self.token_count += max_tokens  # Estimate
        self.cost += 0.02  # Estimate for dialog generation
        return response

    def generate_structured(
        self,
        prompt: str,
        response_model: type,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: float = 120.0
    ):
        """
        Generate structured output conforming to a Pydantic model.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic BaseModel class to validate response against
            model: Model identifier (defaults to instance default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            Instance of response_model populated from LLM response
        """
        # Use provided model or default to Llama model
        selected_model = model or self.default_model

        # Build schema hint from Pydantic model
        schema_hint = self._build_schema_hint(response_model)
        enhanced_prompt = f"{prompt}\n\n{schema_hint}\n\nReturn only valid JSON, no other text."

        def _api_call():
            # Temporarily increase timeout for large requests
            original_timeout = self.client.client.timeout
            self.client.client.timeout = httpx.Timeout(timeout)

            try:
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": enhanced_prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                # Extract content from response
                content = response["choices"][0]["message"]["content"]

                # Clean up JSON - remove markdown code blocks if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]  # Remove ```json
                if content.startswith("```"):
                    content = content[3:]  # Remove ```
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()

                # Parse JSON and validate against model
                try:
                    data = json.loads(content)
                    return response_model(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    raise Exception(f"Failed to parse LLM response as JSON: {e}. Content preview: {content[:500]}")
            finally:
                # Restore original timeout
                self.client.client.timeout = original_timeout

        result = retry_with_backoff(_api_call, max_retries=3, base_delay=2.0)

        # Update token count and cost estimates
        self.token_count += max_tokens
        self.cost += (max_tokens / 1000) * 0.02  # Rough estimate

        return result

    def _build_schema_hint(self, response_model: type) -> str:
        """Build a JSON schema hint from a Pydantic model"""
        try:
            schema = response_model.model_json_schema()
            # Simplify schema for prompt
            return f"Expected JSON schema:\n{json.dumps(schema, indent=2)}"
        except:
            # Fallback to simple field listing
            try:
                fields = response_model.model_fields
                field_hints = [f"  - {name}: {field.annotation}" for name, field in fields.items()]
                return f"Expected fields:\n" + "\n".join(field_hints)
            except:
                return "Return a valid JSON object matching the expected structure."

    def _heuristic_relevance_score(self, query: str, knowledge_item: str) -> float:
        """Fallback heuristic relevance scoring"""
        query_words = set(query.lower().split())
        knowledge_words = set(knowledge_item.lower().split())
        overlap = len(query_words.intersection(knowledge_words))
        total_words = len(query_words.union(knowledge_words))
        return min(1.0, overlap / max(1, total_words / 2))
    

