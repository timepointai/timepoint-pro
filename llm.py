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
import threading
from collections import deque

T = TypeVar('T')


class RateLimiter:
    """
    Thread-safe token bucket rate limiter for API calls.

    Uses a sliding window to track requests and enforces rate limits
    across all instances (global tracking).

    Modes:
    - "free": Conservative limits for free tier (20 req/min, burst 5)
    - "paid": Aggressive limits for paid tier (1000 req/min, burst 50)
    """
    # Class-level (global) tracking across all instances
    _global_lock = threading.Lock()
    _global_request_times: deque = deque()
    _global_enabled = True
    _global_mode = "paid"  # Current mode: "free" or "paid" (DEFAULT: paid)

    def __init__(
        self,
        max_requests_per_minute: int = 1000,
        burst_size: int = 50,
        mode: str = "paid"
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst size
            mode: Rate limit mode ("free" or "paid")
        """
        self.mode = mode
        self.max_requests_per_minute = max_requests_per_minute
        self.burst_size = burst_size
        self.min_interval = 60.0 / max_requests_per_minute if max_requests_per_minute > 0 else 0.0

    def wait_if_needed(self) -> float:
        """
        Wait if necessary to respect rate limits.

        Returns:
            float: Seconds waited (0.0 if no wait needed)
        """
        if not RateLimiter._global_enabled:
            return 0.0

        with RateLimiter._global_lock:
            now = time.time()

            # Remove requests older than 60 seconds (sliding window)
            while RateLimiter._global_request_times and \
                  now - RateLimiter._global_request_times[0] > 60.0:
                RateLimiter._global_request_times.popleft()

            # Check if we're at the rate limit
            if len(RateLimiter._global_request_times) >= self.max_requests_per_minute:
                # Calculate how long to wait
                oldest_request = RateLimiter._global_request_times[0]
                wait_time = 60.0 - (now - oldest_request) + 0.1  # Add 100ms buffer

                if wait_time > 0:
                    print(f"    ⏱️  Rate limit reached ({len(RateLimiter._global_request_times)}/{self.max_requests_per_minute} requests/min)")
                    print(f"    ⏳ Waiting {wait_time:.1f}s before next API call...")
                    time.sleep(wait_time)
                    now = time.time()

            # Check burst size (prevent too many requests in short period)
            recent_requests = sum(1 for t in RateLimiter._global_request_times if now - t < 5.0)
            if recent_requests >= self.burst_size:
                # Enforce minimum interval between requests
                if RateLimiter._global_request_times:
                    last_request = RateLimiter._global_request_times[-1]
                    time_since_last = now - last_request
                    if time_since_last < self.min_interval:
                        wait_time = self.min_interval - time_since_last
                        print(f"    ⏳ Burst control: waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        now = time.time()

            # Record this request
            RateLimiter._global_request_times.append(now)

            return 0.0

    @classmethod
    def disable_globally(cls):
        """Disable rate limiting globally (for testing)"""
        cls._global_enabled = False
        print("⚠️  Rate limiting DISABLED globally")

    @classmethod
    def enable_globally(cls):
        """Enable rate limiting globally"""
        cls._global_enabled = True
        print("✓ Rate limiting ENABLED globally")

    @classmethod
    def set_mode(cls, mode: str):
        """Set global rate limiting mode"""
        if mode not in ["free", "paid"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'free' or 'paid'")
        cls._global_mode = mode
        print(f"🔄 Rate limiter mode set to: {mode.upper()}")

    @classmethod
    def get_mode(cls) -> str:
        """Get current global mode"""
        return cls._global_mode

    @classmethod
    def reset(cls):
        """Reset global rate limit tracking"""
        with cls._global_lock:
            cls._global_request_times.clear()
            print("🔄 Rate limiter reset")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get current rate limiting statistics"""
        with cls._global_lock:
            now = time.time()
            recent_1min = sum(1 for t in cls._global_request_times if now - t < 60.0)
            recent_5sec = sum(1 for t in cls._global_request_times if now - t < 5.0)

            return {
                "enabled": cls._global_enabled,
                "mode": cls._global_mode,
                "total_requests": len(cls._global_request_times),
                "requests_last_minute": recent_1min,
                "requests_last_5sec": recent_5sec,
            }


class OpenRouterClient:
    """Custom HTTP client for OpenRouter API (replaces OpenAI client)"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_requests_per_minute: int = 1000,
        burst_size: int = 50,
        mode: str = "paid"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        # Explicit timeout configuration to prevent hangs:
        # - connect: 10s for connection establishment
        # - read: 120s for slow LLM responses (increased from 60s)
        # - write: 30s for request body upload
        # - pool: 10s for getting a connection from the pool
        self.client = httpx.Client(timeout=httpx.Timeout(
            connect=10.0,
            read=120.0,
            write=30.0,
            pool=10.0
        ))

        # Initialize rate limiter
        self.mode = mode
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=max_requests_per_minute,
            burst_size=burst_size,
            mode=mode
        )

    @property
    def chat(self):
        """Return self to mimic OpenAI client structure"""
        return self

    @property
    def completions(self):
        """Return self to mimic OpenAI client structure"""
        return self

    def create(self, **kwargs):
        """Make a chat completion request to OpenRouter with rate limiting"""
        # Apply rate limiting before making request
        self.rate_limiter.wait_if_needed()

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

        max_retries = 3
        retry_delay = 2.0

        for attempt in range(max_retries):
            try:
                response = self.client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                # Handle rate limit errors (429) with exponential backoff
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"    ⚠️  Rate limit (429) from API - waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"OpenRouter API rate limit exceeded after {max_retries} retries")

                # Handle other HTTP errors
                raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"    ⚠️  Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"    ⏳ Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Request failed after {max_retries} retries: {str(e)}")

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


class FreeModelSelector:
    """
    Dynamic selector for OpenRouter free models.

    OpenRouter offers free models (identified by ':free' suffix) that rotate availability.
    This class queries the API to discover currently available free models and selects
    the best one based on user preference (quality vs speed).

    Usage:
        selector = FreeModelSelector(api_key)
        best_model = selector.get_best_free_model()  # Quality-focused
        fast_model = selector.get_fastest_free_model()  # Speed-focused
        selector.list_free_models()  # Display all available

    Free Model Characteristics (as of Dec 2024):
        - Suffix: Models end with ':free' (e.g., 'meta-llama/llama-3.3-70b-instruct:free')
        - Rate limits: More restrictive than paid tier
        - Availability: May change without notice (rotating selection)
        - Quality: Varies - some are very capable (Llama 70B, Qwen 235B)
    """

    # Known high-quality free models (ranked by preference)
    QUALITY_RANKED_MODELS = [
        "qwen/qwen3-235b-a22b:free",  # 235B params, excellent quality
        "meta-llama/llama-3.3-70b-instruct:free",  # Llama 3.3 70B
        "meta-llama/llama-3.1-70b-instruct:free",  # Llama 3.1 70B
        "google/gemini-2.0-flash-exp:free",  # 1M context, fast
        "mistralai/mistral-large-2411:free",  # Mistral Large
    ]

    # Known fast free models (ranked by speed)
    SPEED_RANKED_MODELS = [
        "google/gemini-2.0-flash-exp:free",  # Extremely fast, 1M context
        "meta-llama/llama-3.2-3b-instruct:free",  # Small & fast
        "meta-llama/llama-3.2-1b-instruct:free",  # Tiny & very fast
        "mistralai/mistral-7b-instruct:free",  # 7B fast
    ]

    def __init__(self, api_key: str, cache_ttl_hours: int = 1):
        """
        Initialize free model selector.

        Args:
            api_key: OpenRouter API key
            cache_ttl_hours: How long to cache model list (default: 1 hour for free models)
        """
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._models_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None

    def get_free_models(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all currently available free models from OpenRouter.

        Returns:
            List of model dicts with id, name, context_length, etc.
        """
        now = datetime.now()

        # Check cache
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

            with httpx.Client(timeout=15.0) as http_client:
                response = http_client.get(f"{self.base_url}/models", headers=headers)
                response.raise_for_status()

            models_data = response.json()
            all_models = models_data.get("data", [])

            # Filter for free models (identified by ':free' suffix)
            free_models = []
            for model in all_models:
                model_id = model.get("id", "")
                if model_id.endswith(":free"):
                    free_models.append({
                        "id": model_id,
                        "name": model.get("name", model_id),
                        "context_length": model.get("context_length", 0),
                        "description": model.get("description", ""),
                        "pricing": model.get("pricing", {}),
                        "top_provider": model.get("top_provider", {})
                    })

            # Sort by context length (higher first)
            free_models.sort(key=lambda x: -x["context_length"])

            # Cache results
            self._models_cache = free_models
            self._cache_timestamp = now

            print(f"🆓 Found {len(free_models)} free models on OpenRouter")
            return free_models

        except Exception as e:
            print(f"⚠️ Failed to fetch free models: {e}")
            if self._models_cache is not None:
                print("📋 Using cached free model data")
                return self._models_cache
            return []

    def get_best_free_model(self) -> Optional[str]:
        """
        Get the best available free model (quality-focused).

        Checks known high-quality models first, then falls back to
        largest context length available.

        Returns:
            Model ID string or None if no free models available
        """
        available = {m["id"] for m in self.get_free_models()}

        if not available:
            print("⚠️ No free models currently available")
            return None

        # Check quality-ranked models first
        for model in self.QUALITY_RANKED_MODELS:
            if model in available:
                print(f"🌟 Selected best free model: {model}")
                return model

        # Fallback to largest context model
        models = self.get_free_models()
        if models:
            best = models[0]  # Already sorted by context length
            print(f"🌟 Selected free model (largest context): {best['id']}")
            return best["id"]

        return None

    def get_fastest_free_model(self) -> Optional[str]:
        """
        Get the fastest available free model (speed-focused).

        Prioritizes known fast models, then smaller models by context size.

        Returns:
            Model ID string or None if no free models available
        """
        available = {m["id"] for m in self.get_free_models()}

        if not available:
            print("⚠️ No free models currently available")
            return None

        # Check speed-ranked models first
        for model in self.SPEED_RANKED_MODELS:
            if model in available:
                print(f"⚡ Selected fastest free model: {model}")
                return model

        # Fallback to smallest context model (usually faster)
        models = self.get_free_models()
        if models:
            # Sort by context ascending (smaller = usually faster)
            models_sorted = sorted(models, key=lambda x: x["context_length"])
            fastest = models_sorted[0]
            print(f"⚡ Selected free model (smallest/fastest): {fastest['id']}")
            return fastest["id"]

        return None

    def list_free_models(self) -> str:
        """
        Return a formatted string listing all available free models.

        Returns:
            Formatted string for display
        """
        models = self.get_free_models()
        if not models:
            return "🆓 No free models currently available on OpenRouter"

        lines = [
            "🆓 Available FREE Models on OpenRouter:",
            "-" * 60
        ]

        for i, model in enumerate(models, 1):
            ctx_k = model["context_length"] // 1024 if model["context_length"] else 0
            # Mark quality/speed tier
            tier = ""
            if model["id"] in self.QUALITY_RANKED_MODELS[:3]:
                tier = " ⭐ BEST"
            elif model["id"] in self.SPEED_RANKED_MODELS[:3]:
                tier = " ⚡ FAST"

            lines.append(f"  {i:2d}. {model['id']}")
            lines.append(f"      Context: {ctx_k}K{tier}")

        lines.append("-" * 60)
        lines.append(f"Total: {len(models)} free models")
        lines.append("")
        lines.append("Usage: --free (best quality) or --free-fast (speed)")

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

# ============================================================================
# Backward Compatibility Re-exports (classes now live in schemas.py)
# ============================================================================
# These imports maintain backward compatibility for code that does:
#   from llm import EntityPopulation, ValidationResult
# The canonical location is now schemas.py to break circular dependencies.
from schemas import EntityPopulation, ValidationResult

class LLMClient:
    """Unified LLM client with cost tracking and model selection (REAL LLM only)"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: Optional[str] = None,
        model_cache_ttl_hours: int = 24,
        max_requests_per_minute: int = 1000,
        burst_size: int = 50,
        mode: str = "paid"
    ):
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
        self.mode = mode

        # Initialize model manager for Llama models
        self.model_manager = ModelManager(api_key, model_cache_ttl_hours)

        # Set default model based on mode
        if default_model:
            self.default_model = default_model
        elif mode == "paid":
            # Paid mode: Use Llama 4 Scout (327K context, unlimited rate, JSON mode support)
            self.default_model = "meta-llama/llama-4-scout"
        else:
            # Free mode: Use model manager's default selection
            self.default_model = self.model_manager.get_default_model()

        # Set model for ultra-complex tasks (405B for paid, same as default for free)
        if mode == "paid":
            self.ultra_complex_model = "meta-llama/llama-3.1-405b-instruct"  # For >50k token tasks
            self.complex_model = "meta-llama/llama-4-scout"  # Standard complex tasks
        else:
            self.ultra_complex_model = self.default_model
            self.complex_model = self.default_model

        print(f"🦙 LLM Mode: {mode.upper()}")
        print(f"   Default model: {self.default_model}")
        if mode == "paid":
            print(f"   Complex tasks: {self.complex_model}")
            print(f"   Ultra-complex: {self.ultra_complex_model}")
        print(f"📋 Available Llama models: {len(self.model_manager.get_llama_models())} cached")

        # Set global rate limiter mode
        RateLimiter.set_mode(mode)

        # Always create real OpenRouter client with rate limiting
        self.client = OpenRouterClient(
            api_key=api_key,
            base_url=base_url,
            max_requests_per_minute=max_requests_per_minute,
            burst_size=burst_size,
            mode=mode
        )

        # Print rate limit configuration
        if mode == "paid":
            print(f"⏱️  Rate limiting: {max_requests_per_minute} requests/min (PAID - unlimited tier)")
        else:
            print(f"⏱️  Rate limiting: {max_requests_per_minute} requests/min, burst size: {burst_size}")
    
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
                max_tokens=12000,  # Increased from 1000 for Llama 4 Scout
                response_format={"type": "json_object"}  # Force JSON mode
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
                max_tokens=8000,  # Increased from 800 for Llama 4 Scout
                response_format={"type": "json_object"}  # Force JSON mode
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

    def generate_dialog(self, prompt: str, max_tokens: int = 16000, model: Optional[str] = None):  # Increased from 2000
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
- relationship_impacts: object mapping EACH entity_id to a SINGLE float showing their overall relationship change (e.g. {{"alice": 0.1, "bob": -0.05}} means alice's relationships improved overall, bob's declined)
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
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON mode
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
        max_tokens: int = 24000,  # Increased from 4000 for Llama 4 Scout
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
            # Use explicit timeout configuration for consistency
            original_timeout = self.client.client.timeout
            self.client.client.timeout = httpx.Timeout(
                connect=10.0,
                read=timeout,  # Main timeout for slow LLM responses
                write=30.0,
                pool=10.0
            )

            try:
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": enhanced_prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}  # Force JSON mode
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
    

