"""
Natural Language Interface for Timepoint-Pro (Sprint 3)

Convert natural language descriptions into validated simulation configurations,
enabling zero-code simulation generation.

Components:
- NLConfigGenerator: LLM-powered NL → SimulationConfig translation
- ConfigValidator: Semantic validation and constraint checking
- InteractiveRefiner: Interactive config refinement workflow
- ClarificationEngine: Ambiguity detection and clarification questions

Example:
    from nl_interface import NLConfigGenerator

    generator = NLConfigGenerator(api_key="your_openrouter_key")

    config, confidence = generator.generate_config(
        "Simulate the Apollo 13 crisis with 3 astronauts and mission control. "
        "Focus on decision-making under pressure. 10 timepoints covering "
        "the explosion through safe return."
    )

    print(f"Confidence: {confidence:.1%}")
    # config is a validated SimulationConfig ready for execution
"""

from .adapter import NLToProductionAdapter, convert_nl_to_production
from .clarification_engine import Clarification, ClarificationEngine
from .config_validator import ConfigValidator, SimulationConfig, ValidationResult
from .interactive_refiner import CLIRefiner, InteractiveRefiner, RefinementStep
from .nl_to_config import NLConfigGenerator

__all__ = [
    "NLConfigGenerator",
    "ConfigValidator",
    "SimulationConfig",
    "ValidationResult",
    "ClarificationEngine",
    "Clarification",
    "InteractiveRefiner",
    "CLIRefiner",
    "RefinementStep",
    # Production Adapter
    "NLToProductionAdapter",
    "convert_nl_to_production",
]
