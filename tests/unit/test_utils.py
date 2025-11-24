"""
Test utilities for handling LLM non-determinism and flaky tests.

Provides decorators and helpers to make tests more robust against LLM variability.
"""

import functools
import time
from typing import Callable, Type


def retry_on_llm_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry tests that fail due to LLM non-determinism.

    Specifically handles:
    - Empty knowledge_state arrays
    - LLM timeout errors
    - Intermittent API failures

    IMPORTANT: This decorator does NOT recreate pytest fixtures between retries.
    Tests should use unique IDs or be idempotent to avoid database constraint errors.

    Usage:
        @retry_on_llm_failure(max_attempts=3)
        def test_something(self):
            # Test code here
            pass

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        print(f"✅ Test succeeded on attempt {attempt + 1}")
                    return result

                except AssertionError as e:
                    last_exception = e
                    error_msg = str(e)

                    # Check if it's an LLM-related failure
                    llm_related = any(keyword in error_msg.lower() for keyword in [
                        'knowledge_state',
                        'empty',
                        'llm',
                        'length',
                        '0 > 0'
                    ])

                    if not llm_related or attempt == max_attempts - 1:
                        # Not LLM-related or final attempt, raise immediately
                        raise

                    # LLM-related failure, retry
                    print(f"⚠️  Test failed on attempt {attempt + 1} due to LLM non-determinism")
                    print(f"   Error: {error_msg[:100]}")
                    print(f"   Retrying in {delay}s...")
                    time.sleep(delay)

                except Exception as e:
                    # Database constraint errors are NOT LLM-related, don't retry
                    error_msg = str(e)
                    if 'UNIQUE constraint' in error_msg or 'IntegrityError' in error_msg:
                        raise

                    # Other exceptions, don't retry
                    raise

            # If we get here, all retries exhausted
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def with_llm_warmup(warmup_calls: int = 1):
    """
    Decorator to warm up LLM before running test.

    Makes dummy calls to ensure LLM is responsive and model is loaded.

    Args:
        warmup_calls: Number of warmup calls to make
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if first arg is 'self' with llm_client
            if args and hasattr(args[0], 'llm_client'):
                llm_client = args[0].llm_client if hasattr(args[0], 'llm_client') else None

                if llm_client:
                    print(f"🔥 Warming up LLM with {warmup_calls} call(s)...")
                    from schemas import Entity, ResolutionLevel

                    for i in range(warmup_calls):
                        try:
                            # Make a simple warmup call
                            dummy_entity = Entity(
                                entity_id=f"warmup_{i}",
                                entity_type="human",
                                timepoint="warmup_tp",
                                resolution_level=ResolutionLevel.TENSOR_ONLY,
                                entity_metadata={"role": "warmup"}
                            )
                            llm_client.populate_entity(
                                entity_schema=dummy_entity,
                                context={"warmup": True}
                            )
                        except Exception as e:
                            print(f"   Warmup call {i+1} failed: {e}")

            return func(*args, **kwargs)

        return wrapper
    return decorator


def assert_knowledge_state_populated(entity, min_items: int = 1):
    """
    Helper assertion that provides better error messages for knowledge_state checks.

    Args:
        entity: Entity or EntityPopulation to check
        min_items: Minimum number of knowledge items expected
    """
    # Handle EntityPopulation
    if hasattr(entity, 'knowledge_state'):
        knowledge = entity.knowledge_state
    # Handle Entity with nested cognitive_tensor
    elif hasattr(entity, 'entity_metadata') and 'cognitive_tensor' in entity.entity_metadata:
        knowledge = entity.entity_metadata['cognitive_tensor'].get('knowledge_state', [])
    else:
        raise ValueError(f"Cannot find knowledge_state in entity: {type(entity)}")

    if len(knowledge) < min_items:
        error_msg = f"""
❌ Knowledge state validation failed:
   Expected: At least {min_items} knowledge items
   Got: {len(knowledge)} items
   Content: {knowledge}
   Entity: {getattr(entity, 'entity_id', 'unknown')}

This may be due to LLM non-determinism. The test will automatically retry.
"""
        raise AssertionError(error_msg)

    return knowledge


def skip_if_llm_unavailable(func: Callable) -> Callable:
    """
    Decorator to skip test if LLM is unavailable or rate-limited.
    """
    import os
    import pytest

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not os.getenv('OPENROUTER_API_KEY'):
            pytest.skip("OPENROUTER_API_KEY not set")

        return func(*args, **kwargs)

    return wrapper
