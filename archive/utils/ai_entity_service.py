#!/usr/bin/env python3
"""
ai_entity_service.py - AI Entity Service with Internal/External API Support

Provides a comprehensive service for running AI-powered entities with safety controls,
rate limiting, caching, and both internal and public API endpoints.
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any, Tuple
import uuid

import bleach
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field, validator
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
import openai

from schemas import AIEntity, Entity
from llm_v2 import LLMClient  # Use new centralized service
from storage import GraphStore
from validation import Validator


# =============================================================================
# Data Models
# =============================================================================

class AIRequest(BaseModel):
    """Request model for AI entity interactions"""
    entity_id: str = Field(..., description="ID of the AI entity to interact with")
    message: str = Field(..., description="User message to send to the AI entity")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")

    @validator('message')
    def validate_message_length(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        if len(v) > 10000:  # 10KB limit
            raise ValueError('Message too long (max 10000 characters)')
        return v


class AIResponse(BaseModel):
    """Response model for AI entity interactions"""
    entity_id: str
    response: str
    session_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    safety_warnings: List[str] = Field(default_factory=list)


class ServiceHealth(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    entities_loaded: int
    active_sessions: int
    cache_stats: Dict[str, Any]


# =============================================================================
# Safety and Input Processing
# =============================================================================

class InputBleacher:
    """Handles input sanitization and safety filtering"""

    def __init__(self):
        # Dangerous patterns to filter
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'vbscript:',  # VBScript
            r'data:text/html',  # Data URLs
        ]

        # Prompt injection patterns
        self.injection_patterns = [
            r'(?i)ignore.*previous.*instructions',
            r'(?i)forget.*system.*prompt',
            r'(?i)you.*are.*not.*ai',
            r'(?i)bypass.*safety',
            r'(?i)jailbreak',
            r'(?i)override.*restrictions',
        ]

    def bleach_input(self, text: str, rules: List[str]) -> Tuple[str, List[str]]:
        """Apply input bleaching based on entity rules"""
        warnings = []
        cleaned_text = text

        # Apply HTML sanitization
        if "remove_script_tags" in rules:
            cleaned_text = bleach.clean(cleaned_text, tags=[], strip=True)

        # Remove dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                cleaned_text = re.sub(pattern, '[FILTERED]', cleaned_text, flags=re.IGNORECASE)
                warnings.append("Dangerous content filtered")

        # Check for prompt injection
        if "prevent_prompt_injection" in rules:
            for pattern in self.injection_patterns:
                if re.search(pattern, cleaned_text, re.IGNORECASE):
                    warnings.append("Potential prompt injection detected")
                    # Replace with safe version
                    cleaned_text = re.sub(pattern, '[FILTERED]', cleaned_text, flags=re.IGNORECASE)

        # Limit input length
        if "limit_input_length" in rules and len(cleaned_text) > 5000:
            cleaned_text = cleaned_text[:5000] + "..."
            warnings.append("Input truncated due to length")

        return cleaned_text, warnings


class OutputFilter:
    """Handles output filtering and content moderation"""

    def __init__(self):
        self.harmful_patterns = [
            r'(?i)hate.*speech',
            r'(?i)violent.*content',
            r'(?i)illegal.*activities',
            r'(?i)personal.*information',
        ]

    def filter_output(self, text: str, rules: List[str]) -> Tuple[str, List[str]]:
        """Apply output filtering based on entity rules"""
        warnings = []
        filtered_text = text

        # Content moderation
        if "filter_harmful_content" in rules:
            for pattern in self.harmful_patterns:
                if re.search(pattern, filtered_text, re.IGNORECASE):
                    warnings.append("Content moderation triggered")
                    filtered_text = "[CONTENT FILTERED]"

        # PII removal (basic)
        if "remove_pii" in rules:
            # Basic email removal
            filtered_text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', filtered_text)
            # Basic phone number removal
            filtered_text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', filtered_text)

        # Add disclaimers
        disclaimers = []
        if "add_content_warnings" in rules and any(word in filtered_text.lower() for word in ['violence', 'death', 'injury']):
            disclaimers.append("⚠️ This content contains themes that may be disturbing.")
        if "validate_factual_accuracy" in rules:
            disclaimers.append("ℹ️ AI-generated content may not be factually accurate.")

        if disclaimers:
            filtered_text += "\n\n" + "\n".join(disclaimers)

        return filtered_text, warnings


# =============================================================================
# Rate Limiting and Caching
# =============================================================================

class RateLimiter:
    """Simple rate limiter using Redis or in-memory storage"""

    def __init__(self, redis_client=None):
        self.redis = redis_client if REDIS_AVAILABLE and redis_client else None
        self.memory_store = defaultdict(list) if not self.redis else None

    def check_rate_limit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Check if request is within rate limit"""
        now = time.time()

        if self.redis:
            # Redis-based rate limiting
            pipeline = self.redis.pipeline()
            pipeline.zremrangebyscore(key, '-inf', now - window_seconds)
            pipeline.zadd(key, {str(now): now})
            pipeline.zcard(key)
            pipeline.expire(key, window_seconds)
            _, _, count, _ = pipeline.execute()
            return count <= limit
        else:
            # In-memory rate limiting
            timestamps = self.memory_store[key]
            # Remove old timestamps
            timestamps[:] = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True


class ResponseCache:
    """LRU cache for AI responses"""

    def __init__(self, redis_client=None, max_size: int = 1000):
        self.redis = redis_client if REDIS_AVAILABLE and redis_client else None
        self.max_size = max_size
        self.memory_cache = {} if not self.redis else None

    def get(self, key: str) -> Optional[str]:
        """Get cached response"""
        if self.redis:
            return self.redis.get(key)
        elif self.memory_cache is not None:
            entry = self.memory_cache.get(key)
            if entry:
                value, expiry = entry
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove it
                    del self.memory_cache[key]
            return None
        return None

    def set(self, key: str, value: str, ttl: int):
        """Set cached response with TTL"""
        if self.redis:
            self.redis.setex(key, ttl, value)
        elif self.memory_cache is not None:
            if len(self.memory_cache) >= self.max_size:
                # Simple LRU - remove oldest
                oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k][1])
                del self.memory_cache[oldest_key]
            self.memory_cache[key] = (value, time.time() + ttl)


# =============================================================================
# AI Entity Runner
# =============================================================================

class AIEntityRunner:
    """Manages AI entity execution with safety controls"""

    def __init__(self, llm_client: LLMClient, store: GraphStore, config: Dict):
        self.llm_client = llm_client
        self.store = store
        self.config = config

        # Initialize components
        self.bleacher = InputBleacher()
        self.filter = OutputFilter()
        self.rate_limiter = RateLimiter()
        self.cache = ResponseCache()

        # Session management
        self.active_sessions = {}
        self.session_timeout = 3600  # 1 hour

    def load_entity(self, entity_id: str) -> Optional[AIEntity]:
        """Load AI entity from storage"""
        entity = self.store.get_entity(entity_id)
        if not entity or entity.entity_type != "ai":
            return None

        try:
            return AIEntity(**entity.entity_metadata)
        except Exception:
            return None

    def generate_cache_key(self, entity_id: str, message: str, context: Dict) -> str:
        """Generate cache key for request"""
        content = f"{entity_id}:{message}:{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process an AI entity interaction request"""
        # Load entity
        entity = self.load_entity(request.entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="AI entity not found")

        # Rate limiting
        rate_key = f"rate:{request.entity_id}"
        if not self.rate_limiter.check_rate_limit(rate_key, entity.rate_limit_per_minute):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input bleaching
        cleaned_message, bleach_warnings = self.bleacher.bleach_input(
            request.message, entity.input_bleaching_rules
        )

        # Check cache
        cache_key = self.generate_cache_key(request.entity_id, cleaned_message, request.context)
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return AIResponse(
                entity_id=request.entity_id,
                response=cached_response,
                session_id=request.session_id or str(uuid.uuid4()),
                metadata={"cached": True, "bleach_warnings": bleach_warnings}
            )

        # Prepare context for AI
        context = self._build_ai_context(entity, cleaned_message, request.context)

        # Make AI call
        try:
            ai_response = await self.llm_client.generate_response(
                context=context,
                temperature=entity.temperature,
                top_p=entity.top_p,
                max_tokens=entity.max_tokens,
                model=entity.model_name
            )
        except Exception as e:
            # Use fallback response
            fallback = entity.fallback_responses[0] if entity.fallback_responses else "I need a moment to process that."
            ai_response = entity.error_handling.get("api_error", fallback)

        # Output filtering
        filtered_response, filter_warnings = self.filter.filter_output(
            ai_response, entity.output_filtering_rules
        )

        # Cache response
        self.cache.set(cache_key, filtered_response, entity.response_cache_ttl)

        # Update performance metrics (simplified)
        # In real implementation, you'd track this in a database

        return AIResponse(
            entity_id=request.entity_id,
            response=filtered_response,
            session_id=request.session_id or str(uuid.uuid4()),
            metadata={
                "bleach_warnings": bleach_warnings,
                "filter_warnings": filter_warnings,
                "model_used": entity.model_name,
                "tokens_used": len(filtered_response.split())  # Rough estimate
            },
            safety_warnings=bleach_warnings + filter_warnings
        )

    def _build_ai_context(self, entity: AIEntity, message: str, extra_context: Dict) -> Dict:
        """Build context for AI generation"""
        context = {
            "system_prompt": entity.system_prompt,
            "user_message": message,
            "knowledge_base": entity.knowledge_base,
            "behavioral_constraints": entity.behavioral_constraints,
            "safety_level": entity.safety_level
        }

        # Add context injection if enabled
        for key, enabled in entity.context_injection.items():
            if enabled and key in extra_context:
                context[key] = extra_context[key]

        return context


# =============================================================================
# API Service
# =============================================================================

class AIEntityService:
    """FastAPI service for AI entity interactions"""

    def __init__(self, config: Optional[Dict] = None, store: Optional[GraphStore] = None, llm_client: Optional[LLMClient] = None):
        # Support both old signature (config dict) and new signature (store, llm_client)
        if config is None and store is None and llm_client is None:
            # Default empty config
            config = {}

        if config is not None and store is None and llm_client is None:
            # Old signature: config dict
            self.config = config
            self.llm_client = LLMClient(config)
            self.store = GraphStore()
        else:
            # New signature: explicit store and llm_client
            self.config = config or {}
            self.llm_client = llm_client or LLMClient(self.config)
            self.store = store or GraphStore()

        self.app = FastAPI(
            title="AI Entity Service",
            description="API for interacting with AI-powered entities",
            version="1.0.0"
        )

        # Initialize runner
        self.runner = AIEntityRunner(self.llm_client, self.store, self.config)

        # Security
        self.security = HTTPBearer() if self.config.get("api_keys_required", True) else None
        self.api_keys = self.config.get("api_keys", [])

        # Setup middleware
        self._setup_middleware()

        # Setup routes
        self._setup_routes()

    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        if self.config.get("cors_enabled", True):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.get("cors_origins", ["*"]),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

    def register_entity(self, entity):
        """
        Register an AI entity with the service.

        Args:
            entity: AIEntity to register
        """
        # Save to store
        if self.store:
            self.store.save_entity(entity)

        # Could add to in-memory registry if needed
        return entity

    def train_entity(self, entity_id: str, training_data: list):
        """
        Train an AI entity with provided training data.

        Args:
            entity_id: ID of the entity to train
            training_data: List of training examples (dicts with 'query' and 'response')

        Returns:
            Training summary
        """
        # Get entity
        entity = self.store.get_entity(entity_id) if self.store else None
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # For now, just update metadata with training examples count
        # In a full implementation, this would fine-tune the model or update knowledge base
        if 'training_examples' not in entity.entity_metadata:
            entity.entity_metadata['training_examples'] = []

        entity.entity_metadata['training_examples'].extend(training_data)
        entity.training_count = len(entity.entity_metadata['training_examples'])

        # Save updated entity
        if self.store:
            self.store.save_entity(entity)

        return {
            "entity_id": entity_id,
            "training_examples_added": len(training_data),
            "total_training_examples": entity.training_count
        }

    def generate_response(self, entity_id: str, query: str) -> str:
        """
        Generate a response from an AI entity.

        Args:
            entity_id: ID of the entity
            query: User query

        Returns:
            Generated response string
        """
        # Get entity
        entity = self.store.get_entity(entity_id) if self.store else None
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # Get AI config from metadata
        ai_config = entity.entity_metadata.get('ai_config', {})
        system_prompt = ai_config.get('system_prompt', 'You are a helpful assistant.')

        # Use LLM to generate response
        # For now, return a simple response based on training data
        training_examples = entity.entity_metadata.get('training_examples', [])

        # Simple mock response that uses training data
        response = f"Based on my knowledge: "
        if training_examples:
            response += f"I have been trained on {len(training_examples)} examples. "

        response += f"Regarding '{query}': This is a response about the topic."

        # Increment query count
        entity.query_count += 1
        if self.store:
            self.store.save_entity(entity)

        return response

    def save_entity_state(self, entity_id: str):
        """
        Save the current state of an AI entity.

        Args:
            entity_id: ID of the entity to save
        """
        # Entity state is already saved in store, this is a no-op
        # but included for API completeness
        entity = self.store.get_entity(entity_id) if self.store else None
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # Force a save
        if self.store:
            self.store.save_entity(entity)

        return {"entity_id": entity_id, "status": "saved"}

    def get_entity(self, entity_id: str):
        """
        Retrieve an AI entity.

        Args:
            entity_id: ID of the entity

        Returns:
            Entity object
        """
        if not self.store:
            raise ValueError("No store configured")

        return self.store.get_entity(entity_id)

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/health", response_model=ServiceHealth)
        async def health_check():
            """Health check endpoint"""
            return ServiceHealth(
                status="healthy",
                timestamp=datetime.now(),
                entities_loaded=len([]),  # Would track loaded entities
                active_sessions=len(self.runner.active_sessions),
                cache_stats={"enabled": self.config.get("cache_enabled", True)}
            )

        @self.app.post("/ai/chat", response_model=AIResponse)
        async def chat_with_ai(
            request: AIRequest,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(self.security)
        ):
            """Chat with an AI entity"""
            # API key validation
            if self.security and credentials:
                if credentials.credentials not in self.api_keys:
                    raise HTTPException(status_code=401, detail="Invalid API key")

            return await self.runner.process_request(request)

        @self.app.get("/ai/entities")
        async def list_ai_entities():
            """List available AI entities"""
            # Would query database for AI entities
            return {"entities": []}

        @self.app.get("/ai/{entity_id}/config")
        async def get_entity_config(entity_id: str):
            """Get AI entity configuration (filtered for safety)"""
            entity = self.runner.load_entity(entity_id)
            if not entity:
                raise HTTPException(status_code=404, detail="AI entity not found")

            # Return safe subset of configuration
            return {
                "entity_id": entity_id,
                "model_name": entity.model_name,
                "safety_level": entity.safety_level,
                "max_tokens": entity.max_tokens,
                "rate_limit_per_minute": entity.rate_limit_per_minute
            }

    def run(self, host: str = "localhost", port: int = 8001):
        """Run the service"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=self.config.get("log_level", "INFO").lower()
        )


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Main entry point for AI Entity Service"""
    import argparse
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    parser = argparse.ArgumentParser(description="AI Entity Service")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--config", default="conf/config.yaml", help="Configuration file")
    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except:
        # Fallback configuration
        config = {
            "ai_entity_service": {
                "host": args.host,
                "port": args.port,
                "enabled": True,
                "api_keys_required": False,
                "log_level": "INFO"
            },
            "llm": {
                "api_key": "test",
                "base_url": "https://api.openai.com/v1"
            }
        }

    # Initialize and run service
    service = AIEntityService(config.get("ai_entity_service", {}))
    service.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
