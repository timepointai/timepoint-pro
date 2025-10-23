"""
Mechanism Tracking - Decorator for automatic mechanism usage tracking

Usage:
    @track_mechanism("M1", "heterogeneous_fidelity")
    def assign_resolution(entity, resolution):
        ...

This automatically records when mechanisms are used.
"""

from functools import wraps
from typing import Optional, Callable, Any
from .run_tracker import MetadataManager
import threading

# Thread-local storage for current run_id
_thread_local = threading.local()


def set_current_run_id(run_id: str):
    """Set the run_id for the current thread"""
    _thread_local.run_id = run_id


def get_current_run_id() -> Optional[str]:
    """Get the run_id for the current thread"""
    return getattr(_thread_local, 'run_id', None)


def clear_current_run_id():
    """Clear the run_id for the current thread"""
    if hasattr(_thread_local, 'run_id'):
        del _thread_local.run_id


# Global metadata manager instance
_metadata_manager: Optional[MetadataManager] = None


def get_metadata_manager() -> Optional[MetadataManager]:
    """Get the global metadata manager"""
    return _metadata_manager


def set_metadata_manager(manager: MetadataManager):
    """Set the global metadata manager"""
    global _metadata_manager
    _metadata_manager = manager


def track_mechanism(mechanism: str, description: str = ""):
    """
    Decorator to track mechanism usage.

    Args:
        mechanism: Mechanism ID (M1, M2, etc.)
        description: Optional description of what this tracks

    Example:
        @track_mechanism("M1", "heterogeneous_fidelity")
        def assign_resolution(entity, resolution):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)

            # Record mechanism usage if tracking is active
            run_id = get_current_run_id()
            manager = get_metadata_manager()

            if run_id and manager:
                try:
                    context = {
                        "description": description,
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_count": len(kwargs)
                    }
                    manager.record_mechanism(run_id, mechanism, func.__name__, context)
                except Exception as e:
                    # Don't fail the function if tracking fails
                    print(f"Warning: Failed to track mechanism {mechanism}: {e}")

            return result

        # Add metadata attributes
        wrapper._mechanism = mechanism
        wrapper._mechanism_description = description

        return wrapper
    return decorator


def track_resolution(run_id: str, entity_id: str, resolution, timepoint_id: str):
    """
    Manually track resolution assignment.

    Used when @track_mechanism decorator can't be used.
    """
    manager = get_metadata_manager()
    if manager:
        try:
            manager.record_resolution(run_id, entity_id, resolution, timepoint_id)
        except Exception as e:
            print(f"Warning: Failed to track resolution: {e}")


def track_validation(run_id: str, validator_name: str, passed: bool, message: str = None, violations: list = None):
    """
    Manually track validation execution.

    Used when @track_mechanism decorator can't be used.
    """
    manager = get_metadata_manager()
    if manager:
        try:
            manager.record_validation(run_id, validator_name, passed, message, violations)
        except Exception as e:
            print(f"Warning: Failed to track validation: {e}")
