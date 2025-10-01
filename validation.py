# ============================================================================
# validation.py - Validation framework with plugin registry
# ============================================================================
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable
import numpy as np

from schemas import Entity, ExposureEvent

class Validator(ABC):
    """Base validator with plugin registry"""
    _validators = {}
    
    @classmethod
    def register(cls, name: str, severity: str = "ERROR"):
        def decorator(func: Callable):
            cls._validators[name] = {"func": func, "severity": severity}
            return func
        return decorator
    
    @classmethod
    def validate_all(cls, entity: Entity, context: Dict) -> List[Dict]:
        violations = []
        for name, validator in cls._validators.items():
            result = validator["func"](entity, context)
            if not result["valid"]:
                violations.append({
                    "validator": name,
                    "severity": validator["severity"],
                    "message": result["message"]
                })
        return violations

@Validator.register("information_conservation", "ERROR")
def validate_information_conservation(entity: Entity, context: Dict, store=None) -> Dict:
    """Validate knowledge ⊆ exposure history"""
    # If store is provided, query actual exposure events from database
    if store:
        exposure_events = store.get_exposure_events(entity.entity_id)
        exposure = set(event.information for event in exposure_events)
    else:
        # Fallback to context-based validation for backward compatibility
        exposure = set(context.get("exposure_history", []))

    knowledge = set(entity.entity_metadata.get("knowledge_state", []))

    unknown = knowledge - exposure
    if unknown:
        return {"valid": False, "message": f"Entity knows about {unknown} without exposure"}
    return {"valid": True, "message": "Information conservation satisfied"}

@Validator.register("energy_budget", "WARNING")
def validate_energy_budget(entity: Entity, context: Dict) -> Dict:
    """Validate interaction costs ≤ capacity"""
    budget = entity.entity_metadata.get("energy_budget", 100)
    expenditure = sum(context.get("interactions", []))
    
    if expenditure > budget * 1.2:  # Allow 20% temporary excess
        return {"valid": False, "message": f"Energy expenditure {expenditure} exceeds budget {budget}"}
    return {"valid": True, "message": "Energy budget satisfied"}

@Validator.register("behavioral_inertia", "WARNING")
def validate_behavioral_inertia(entity: Entity, context: Dict) -> Dict:
    """Validate personality drift is gradual"""
    if "previous_personality" not in context:
        return {"valid": True, "message": "No previous state to compare"}
    
    current = np.array(entity.entity_metadata.get("personality_traits", []))
    previous = np.array(context["previous_personality"])
    
    drift = np.linalg.norm(current - previous)
    if drift > 0.5:  # Threshold
        return {"valid": False, "message": f"Personality drift {drift} exceeds threshold"}
    return {"valid": True, "message": "Behavioral inertia satisfied"}

@Validator.register("biological_constraints", "ERROR")
def validate_biological_constraints(entity: Entity, context: Dict) -> Dict:
    """Validate age-dependent capabilities"""
    age = entity.entity_metadata.get("age", 0)
    action = context.get("action", "")
    
    if age > 100 and "physical_labor" in action:
        return {"valid": False, "message": f"Entity age {age} incompatible with physical labor"}
    if age < 18 and age > 50 and "childbirth" in action:
        return {"valid": False, "message": f"Entity age {age} incompatible with childbirth"}
    
    return {"valid": True, "message": "Biological constraints satisfied"}