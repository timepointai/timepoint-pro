"""
Interactive Configuration Refiner

Provides interactive workflow for refining and approving simulation configurations
with preview, clarification, and iterative adjustment capabilities.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
import json

from .nl_to_config import NLConfigGenerator
from .config_validator import ValidationResult
from .clarification_engine import ClarificationEngine, Clarification


@dataclass
class RefinementStep:
    """A step in the refinement process"""
    step_type: str  # "clarification", "generation", "preview", "adjustment", "approval"
    description: str
    data: Optional[Dict[str, Any]] = None


class InteractiveRefiner:
    """
    Interactive configuration refinement workflow.

    Manages the complete flow from initial NL description to approved config:
    1. Detect ambiguities and ask clarifications
    2. Generate initial config
    3. Preview and validate
    4. Allow iterative adjustments
    5. Final approval

    Example:
        refiner = InteractiveRefiner(api_key="your_key")

        # Start refinement
        result = refiner.start_refinement("Simulate a board meeting with 5 executives")

        # Review clarifications
        if result["clarifications_needed"]:
            for clarification in result["clarifications"]:
                print(f"Q: {clarification.question}")

            # Answer clarifications
            answers = {
                "timepoint_count": "10",
                "focus": "dialog, decision_making"
            }
            result = refiner.answer_clarifications(answers)

        # Preview config
        config = result["config"]
        print(json.dumps(config, indent=2))

        # Approve or adjust
        if result["validation"].is_valid:
            final_config = refiner.approve_config()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        interactive_mode: bool = True,
        auto_approve_threshold: float = 0.95
    ):
        """
        Initialize interactive refiner.

        Args:
            api_key: OpenRouter API key (or None for mock mode)
            interactive_mode: Enable interactive prompts (vs. programmatic)
            auto_approve_threshold: Auto-approve configs above this confidence
        """
        self.generator = NLConfigGenerator(api_key=api_key)
        self.clarification_engine = ClarificationEngine()
        self.interactive_mode = interactive_mode
        self.auto_approve_threshold = auto_approve_threshold

        # State tracking
        self.original_description: Optional[str] = None
        self.current_description: Optional[str] = None
        self.current_config: Optional[Dict[str, Any]] = None
        self.current_validation: Optional[ValidationResult] = None
        self.pending_clarifications: List[Clarification] = []
        self.refinement_history: List[RefinementStep] = []

    def start_refinement(
        self,
        description: str,
        skip_clarifications: bool = False
    ) -> Dict[str, Any]:
        """
        Start refinement workflow from natural language description.

        Args:
            description: Natural language description of scenario
            skip_clarifications: Skip clarification phase and generate immediately

        Returns:
            Dictionary with:
                - clarifications_needed: bool
                - clarifications: List[Clarification] (if needed)
                - config: Dict (if generated)
                - validation: ValidationResult (if generated)
                - next_step: str (what to do next)
        """
        self.original_description = description
        self.current_description = description
        self.refinement_history = []

        # Add start step
        self.refinement_history.append(RefinementStep(
            step_type="start",
            description="Started refinement workflow",
            data={"original_description": description}
        ))

        if skip_clarifications:
            # Generate immediately
            return self._generate_config()

        # Detect ambiguities
        clarifications = self.clarification_engine.detect_ambiguities(description)

        if clarifications:
            self.pending_clarifications = clarifications
            self.refinement_history.append(RefinementStep(
                step_type="clarification",
                description=f"Detected {len(clarifications)} clarifications needed",
                data={"clarifications": [c.field for c in clarifications]}
            ))

            return {
                "clarifications_needed": True,
                "clarifications": clarifications,
                "config": None,
                "validation": None,
                "next_step": "answer_clarifications"
            }
        else:
            # No clarifications needed, generate config
            return self._generate_config()

    def answer_clarifications(
        self,
        answers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Answer pending clarifications and continue refinement.

        Args:
            answers: Dictionary mapping clarification field → answer

        Returns:
            Result dictionary (same format as start_refinement)
        """
        if not self.pending_clarifications:
            raise ValueError("No pending clarifications to answer")

        # Incorporate answers into description
        for clarification in self.pending_clarifications:
            if clarification.field in answers:
                answer = answers[clarification.field]
                self.current_description = self.clarification_engine.answer_clarification(
                    clarification,
                    answer,
                    self.current_description
                )

        # Record step
        self.refinement_history.append(RefinementStep(
            step_type="clarification_answered",
            description=f"Answered {len(answers)} clarifications",
            data={"answers": answers}
        ))

        # Clear pending clarifications
        self.pending_clarifications = []

        # Generate config with enriched description
        return self._generate_config()

    def _generate_config(self) -> Dict[str, Any]:
        """Generate configuration from current description"""
        # Generate config
        config, confidence = self.generator.generate_config(self.current_description)

        # Validate
        validation = self.generator.validate_config(config)

        # Store state
        self.current_config = config
        self.current_validation = validation

        # Record step
        self.refinement_history.append(RefinementStep(
            step_type="generation",
            description=f"Generated config with {confidence:.1%} confidence",
            data={"confidence": confidence}
        ))

        # Determine next step
        if not validation.is_valid:
            next_step = "fix_errors"
        elif confidence >= self.auto_approve_threshold and not validation.warnings:
            next_step = "auto_approved"
        else:
            next_step = "preview_and_approve"

        return {
            "clarifications_needed": False,
            "clarifications": [],
            "config": config,
            "validation": validation,
            "confidence": confidence,
            "next_step": next_step
        }

    def preview_config(self, format: str = "json") -> str:
        """
        Get preview of current configuration.

        Args:
            format: Preview format ("json", "summary", "detailed")

        Returns:
            Preview string
        """
        if not self.current_config:
            return "No configuration generated yet."

        if format == "json":
            return json.dumps(self.current_config, indent=2)

        elif format == "summary":
            config = self.current_config
            summary = f"""
Configuration Summary:
- Scenario: {config.get('scenario', 'N/A')}
- Entities: {len(config.get('entities', []))}
- Timepoints: {config.get('timepoint_count', 'N/A')}
- Temporal Mode: {config.get('temporal_mode', 'N/A')}
- Focus: {', '.join(config.get('focus', []))}
- Outputs: {', '.join(config.get('outputs', []))}
"""
            if self.current_validation:
                summary += f"\nValidation: {'✓ Valid' if self.current_validation.is_valid else '✗ Invalid'}"
                summary += f"\nConfidence: {self.current_validation.confidence_score:.1%}"

                if self.current_validation.warnings:
                    summary += f"\nWarnings: {len(self.current_validation.warnings)}"

            return summary.strip()

        elif format == "detailed":
            preview = self.preview_config("summary")
            preview += "\n\nEntities:\n"
            for entity in self.current_config.get('entities', []):
                preview += f"  - {entity['name']} ({entity['role']})\n"

            if self.current_validation and self.current_validation.warnings:
                preview += "\nWarnings:\n"
                for warning in self.current_validation.warnings:
                    preview += f"  - {warning}\n"

            if self.current_validation and self.current_validation.suggestions:
                preview += "\nSuggestions:\n"
                for suggestion in self.current_validation.suggestions:
                    preview += f"  - {suggestion}\n"

            return preview

        else:
            raise ValueError(f"Unknown preview format: {format}")

    def adjust_config(
        self,
        adjustments: Dict[str, Any],
        regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Adjust configuration parameters.

        Args:
            adjustments: Dictionary of field → new value
            regenerate: If True, regenerate config with adjustments; if False, directly modify

        Returns:
            Result dictionary with updated config and validation
        """
        if not self.current_config:
            raise ValueError("No configuration to adjust")

        if regenerate:
            # Add adjustments to description and regenerate
            adjustment_text = self._format_adjustments_as_text(adjustments)
            self.current_description = f"{self.current_description} {adjustment_text}"

            # Record step
            self.refinement_history.append(RefinementStep(
                step_type="adjustment_regenerate",
                description="Regenerating config with adjustments",
                data={"adjustments": adjustments}
            ))

            return self._generate_config()

        else:
            # Directly modify config
            for field, value in adjustments.items():
                self._apply_adjustment(field, value)

            # Re-validate
            validation = self.generator.validate_config(self.current_config)
            self.current_validation = validation

            # Record step
            self.refinement_history.append(RefinementStep(
                step_type="adjustment_direct",
                description="Directly adjusted config",
                data={"adjustments": adjustments}
            ))

            return {
                "clarifications_needed": False,
                "clarifications": [],
                "config": self.current_config,
                "validation": validation,
                "confidence": validation.confidence_score,
                "next_step": "preview_and_approve"
            }

    def _apply_adjustment(self, field: str, value: Any):
        """Apply a direct adjustment to current config"""
        if "." in field:
            # Nested field (e.g., "entities.0.name")
            parts = field.split(".")
            target = self.current_config
            for part in parts[:-1]:
                if part.isdigit():
                    target = target[int(part)]
                else:
                    target = target[part]
            target[parts[-1]] = value
        else:
            # Top-level field
            self.current_config[field] = value

    def _format_adjustments_as_text(self, adjustments: Dict[str, Any]) -> str:
        """Format adjustments as natural language text"""
        parts = []
        for field, value in adjustments.items():
            if field == "timepoint_count":
                parts.append(f"Use {value} timepoints.")
            elif field == "temporal_mode":
                parts.append(f"Use {value} temporal mode.")
            elif field == "focus":
                parts.append(f"Focus on {', '.join(value) if isinstance(value, list) else value}.")
            elif field == "outputs":
                parts.append(f"Output {', '.join(value) if isinstance(value, list) else value}.")
            else:
                parts.append(f"{field}: {value}.")

        return " ".join(parts)

    def approve_config(self) -> Dict[str, Any]:
        """
        Approve current configuration as final.

        Returns:
            Final approved configuration
        """
        if not self.current_config:
            raise ValueError("No configuration to approve")

        if not self.current_validation or not self.current_validation.is_valid:
            raise ValueError("Cannot approve invalid configuration. Fix errors first.")

        # Record approval
        self.refinement_history.append(RefinementStep(
            step_type="approval",
            description="Configuration approved",
            data={"final_config": self.current_config}
        ))

        return self.current_config

    def reject_and_restart(self, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Reject current config and restart from original description.

        Args:
            reason: Optional reason for rejection

        Returns:
            Fresh start result
        """
        # Record rejection BEFORE resetting
        self.refinement_history.append(RefinementStep(
            step_type="rejection",
            description=f"Configuration rejected: {reason or 'User requested restart'}",
            data={"reason": reason}
        ))

        # Save history before restart
        saved_history = self.refinement_history.copy()

        # Reset to original description
        self.current_description = self.original_description
        self.current_config = None
        self.current_validation = None
        self.pending_clarifications = []

        # Restart (this will reset history, so restore it)
        result = self.start_refinement(self.original_description)

        # Restore history with rejection step
        self.refinement_history = saved_history + self.refinement_history

        return result

    def get_refinement_history(self) -> List[RefinementStep]:
        """Get history of refinement steps"""
        return self.refinement_history.copy()

    def export_refinement_trace(self) -> Dict[str, Any]:
        """
        Export complete refinement trace for debugging/analysis.

        Returns:
            Dictionary with full trace
        """
        return {
            "original_description": self.original_description,
            "final_description": self.current_description,
            "final_config": self.current_config,
            "final_validation": {
                "is_valid": self.current_validation.is_valid if self.current_validation else None,
                "errors": self.current_validation.errors if self.current_validation else [],
                "warnings": self.current_validation.warnings if self.current_validation else [],
                "confidence": self.current_validation.confidence_score if self.current_validation else None
            } if self.current_validation else None,
            "steps": [
                {
                    "step_type": step.step_type,
                    "description": step.description,
                    "data": step.data
                }
                for step in self.refinement_history
            ]
        }


class CLIRefiner:
    """
    Command-line interface wrapper for InteractiveRefiner.

    Provides a simple CLI workflow for interactive refinement.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize CLI refiner"""
        self.refiner = InteractiveRefiner(api_key=api_key, interactive_mode=True)

    def run(self, description: str) -> Dict[str, Any]:
        """
        Run interactive refinement workflow from CLI.

        Args:
            description: Natural language description

        Returns:
            Final approved configuration
        """
        print("\n=== Timepoint-Pro Configuration Refinement ===\n")
        print(f"Description: {description}\n")

        # Start refinement
        result = self.refiner.start_refinement(description)

        # Handle clarifications
        if result["clarifications_needed"]:
            print("Some clarifications needed:\n")
            answers = {}

            for clarification in result["clarifications"]:
                print(f"\nQ: {clarification.question}")
                print(f"   Priority: {'Critical' if clarification.priority == 1 else 'Important' if clarification.priority == 2 else 'Optional'}")
                print(f"   Suggestions:")
                for suggestion in clarification.suggestions:
                    print(f"     - {suggestion}")

                answer = input(f"\nYour answer (or press Enter to skip): ").strip()
                if answer:
                    answers[clarification.field] = answer

            if answers:
                result = self.refiner.answer_clarifications(answers)
            else:
                print("\nNo answers provided. Generating config with available information...")
                result = self.refiner._generate_config()

        # Preview config
        print("\n=== Generated Configuration ===\n")
        print(self.refiner.preview_config(format="detailed"))

        # Show validation
        if result["validation"]:
            print(f"\n=== Validation ===")
            print(f"Valid: {result['validation'].is_valid}")
            print(f"Confidence: {result['validation'].confidence_score:.1%}")

            if result["validation"].warnings:
                print(f"\nWarnings:")
                for warning in result["validation"].warnings:
                    print(f"  - {warning}")

            if result["validation"].errors:
                print(f"\nErrors:")
                for error in result["validation"].errors:
                    print(f"  - {error}")

        # Approval prompt
        if result["validation"] and result["validation"].is_valid:
            approve = input("\nApprove this configuration? (y/n): ").strip().lower()

            if approve == 'y':
                final_config = self.refiner.approve_config()
                print("\n✓ Configuration approved!")
                return final_config
            else:
                print("\nConfiguration not approved. You can adjust parameters or restart.")
                return None
        else:
            print("\nConfiguration has errors and cannot be approved.")
            return None
