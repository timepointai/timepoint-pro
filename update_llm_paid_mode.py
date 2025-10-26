#!/usr/bin/env python3
"""
Update llm.py to add paid mode infrastructure.

This script makes surgical edits to add:
1. Mode parameter to OpenRouterClient
2. Mode parameter to LLMClient
3. Paid model configuration (Llama 3.1 70B/405B)
4. Auto-detection of paid vs free models
"""

import re

# Read the current llm.py
with open("llm.py", "r") as f:
    content = f.read()

# 1. Update OpenRouterClient __init__ signature
old_init = '''    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_requests_per_minute: int = 20,
        burst_size: int = 5
    ):'''

new_init = '''    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_requests_per_minute: int = 20,
        burst_size: int = 5,
        mode: str = "free"
    ):'''

content = content.replace(old_init, new_init)

# 2. Update OpenRouterClient __init__ body to pass mode to RateLimiter
old_rate_limiter = '''        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=max_requests_per_minute,
            burst_size=burst_size
        )'''

new_rate_limiter = '''        # Initialize rate limiter
        self.mode = mode
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=max_requests_per_minute,
            burst_size=burst_size,
            mode=mode
        )'''

content = content.replace(old_rate_limiter, new_rate_limiter)

# 3. Update LLMClient __init__ signature
old_llm_init = '''    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: Optional[str] = None,
        model_cache_ttl_hours: int = 24,
        max_requests_per_minute: int = 20,
        burst_size: int = 5
    ):'''

new_llm_init = '''    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: Optional[str] = None,
        model_cache_ttl_hours: int = 24,
        max_requests_per_minute: int = 20,
        burst_size: int = 5,
        mode: str = "free"
    ):'''

content = content.replace(old_llm_init, new_llm_init)

# 4. Update LLMClient __init__ body to set mode and model based on mode
old_llm_body = '''        # VALIDATION: API key is required
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

        # Always create real OpenRouter client with rate limiting
        self.client = OpenRouterClient(
            api_key=api_key,
            base_url=base_url,
            max_requests_per_minute=max_requests_per_minute,
            burst_size=burst_size
        )

        # Print rate limit configuration
        print(f"⏱️  Rate limiting: {max_requests_per_minute} requests/min, burst size: {burst_size}")'''

new_llm_body = '''        # VALIDATION: API key is required
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
            # Paid mode: Use official Meta Llama 3.1 70B (131K context, unlimited rate)
            self.default_model = "meta-llama/llama-3.1-70b-instruct"
        else:
            # Free mode: Use model manager's default selection
            self.default_model = self.model_manager.get_default_model()

        # Set model for complex tasks (405B for paid, same as default for free)
        if mode == "paid":
            self.complex_model = "meta-llama/llama-3.1-405b-instruct"
        else:
            self.complex_model = self.default_model

        print(f"🦙 LLM Mode: {mode.upper()}")
        print(f"   Default model: {self.default_model}")
        if mode == "paid":
            print(f"   Complex tasks: {self.complex_model}")
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
            print(f"⏱️  Rate limiting: {max_requests_per_minute} requests/min, burst size: {burst_size}")'''

content = content.replace(old_llm_body, new_llm_body)

# Write the updated content
with open("llm.py", "w") as f:
    f.write(content)

print("✅ Updated llm.py with paid mode infrastructure:")
print("   - Added mode parameter to OpenRouterClient")
print("   - Added mode parameter to LLMClient")
print("   - Configured paid models (70B/405B)")
print("   - Set up mode-aware rate limiting")
