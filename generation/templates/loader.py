"""
Template Loader - Single source of truth for Timepoint templates.

This module provides a unified interface to load, validate, and query templates
from the JSON-based template catalog.

Usage:
    from generation.templates.loader import TemplateLoader

    loader = TemplateLoader()

    # List templates
    all_templates = loader.list_templates()
    quick_templates = loader.list_templates(tier="quick")
    core_templates = loader.list_templates(category="core")
    m17_templates = loader.list_templates(mechanism="M17")

    # Load a template
    config = loader.load_template("showcase/board_meeting")

    # Get coverage matrix
    matrix = loader.get_coverage_matrix()

    # Validate templates
    result = loader.validate_template("core/m01_heterogeneous_fidelity")
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from pathlib import Path
from enum import Enum


class TemplateTier(str, Enum):
    """Template complexity tiers."""
    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class TemplateCategory(str, Enum):
    """Template categories."""
    SHOWCASE = "showcase"
    CONVERGENCE = "convergence"


class TemplateStatus(str, Enum):
    """Template validation status."""
    PENDING = "pending"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    BROKEN = "broken"


@dataclass
class TemplateInfo:
    """Information about a template from the catalog."""
    id: str
    name: str
    description: str
    mechanisms: List[str]
    tier: TemplateTier
    category: TemplateCategory
    cost_estimate: str
    duration_estimate: str
    status: TemplateStatus

    @property
    def primary_mechanism(self) -> Optional[str]:
        """Return the primary mechanism (first in list)."""
        return self.mechanisms[0] if self.mechanisms else None


@dataclass
class ValidationResult:
    """Result of template validation."""
    template_id: str
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PatchInfo:
    """Information about a template patch (synth paradigm)."""
    name: str
    category: str
    tags: List[str]
    author: str
    version: str
    description: str


@dataclass
class TemplateCatalog:
    """The full template catalog."""
    version: str
    templates: Dict[str, TemplateInfo]
    mechanisms: Dict[str, str]
    tiers: Dict[str, Dict[str, str]]
    patches: Dict[str, List[str]] = field(default_factory=dict)


class TemplateLoader:
    """
    Unified template loader for Timepoint.

    Provides methods to list, load, validate, and query templates from
    the JSON-based template catalog.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template loader.

        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to the templates directory relative to this file
            self._templates_dir = Path(__file__).parent
        else:
            self._templates_dir = Path(templates_dir)

        self._catalog_path = self._templates_dir / "catalog.json"
        self._catalog: Optional[TemplateCatalog] = None

    def _ensure_catalog_loaded(self) -> None:
        """Load the catalog if not already loaded."""
        if self._catalog is None:
            self._catalog = self._load_catalog()

    def _load_catalog(self) -> TemplateCatalog:
        """Load the catalog from disk."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(f"Template catalog not found: {self._catalog_path}")

        with open(self._catalog_path, "r") as f:
            data = json.load(f)

        templates = {}
        for template_id, info in data.get("templates", {}).items():
            templates[template_id] = TemplateInfo(
                id=template_id,
                name=info.get("name", template_id),
                description=info.get("description", ""),
                mechanisms=info.get("mechanisms", []),
                tier=TemplateTier(info.get("tier", "standard")),
                category=TemplateCategory(info.get("category", "showcase")),
                cost_estimate=info.get("cost_estimate", "unknown"),
                duration_estimate=info.get("duration_estimate", "unknown"),
                status=TemplateStatus(info.get("status", "pending")),
            )

        return TemplateCatalog(
            version=data.get("version", "unknown"),
            templates=templates,
            mechanisms=data.get("mechanisms", {}),
            tiers=data.get("tiers", {}),
            patches=data.get("patches", {}),
        )

    def reload_catalog(self) -> None:
        """Force reload the catalog from disk."""
        self._catalog = self._load_catalog()

    def get_catalog(self) -> TemplateCatalog:
        """Get the full template catalog."""
        self._ensure_catalog_loaded()
        return self._catalog

    def list_templates(
        self,
        tier: Optional[str] = None,
        category: Optional[str] = None,
        mechanism: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TemplateInfo]:
        """
        List templates matching the given filters.

        Args:
            tier: Filter by tier (quick, standard, comprehensive, stress)
            category: Filter by category (core, showcase, portal, stress, convergence)
            mechanism: Filter by mechanism (M1, M2, ..., M18)
            status: Filter by status (pending, verified, deprecated, broken)

        Returns:
            List of TemplateInfo objects matching the filters
        """
        self._ensure_catalog_loaded()

        results = []
        for template_id, info in self._catalog.templates.items():
            # Apply filters
            if tier is not None and info.tier.value != tier:
                continue
            if category is not None and info.category.value != category:
                continue
            if mechanism is not None and mechanism not in info.mechanisms:
                continue
            if status is not None and info.status.value != status:
                continue

            results.append(info)

        return results

    def get_template_info(self, template_id: str) -> Optional[TemplateInfo]:
        """
        Get information about a specific template.

        Args:
            template_id: Template identifier (e.g., "showcase/board_meeting")

        Returns:
            TemplateInfo if found, None otherwise
        """
        self._ensure_catalog_loaded()
        return self._catalog.templates.get(template_id)

    def load_template(self, template_id: str) -> "SimulationConfig":
        """
        Load a template and return a SimulationConfig.

        This method handles both:
        1. New JSON-based templates in category directories
        2. Legacy templates that still exist as class methods

        Args:
            template_id: Template identifier (e.g., "showcase/board_meeting")

        Returns:
            SimulationConfig instance

        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If template JSON is invalid
        """
        self._ensure_catalog_loaded()

        # Check if JSON file exists
        json_path = self._templates_dir / f"{template_id}.json"
        if json_path.exists():
            return self._load_json_template(json_path)

        # Try legacy loading (existing templates in templates/ directory)
        legacy_name = template_id.split("/")[-1]  # e.g., "showcase/board_meeting" -> "board_meeting"
        legacy_path = self._templates_dir / f"{legacy_name}.json"
        if legacy_path.exists():
            return self._load_json_template(legacy_path)

        # Fall back to Python class method (for backward compatibility)
        return self._load_legacy_template(template_id)

    def _load_json_template(self, path: Path) -> "SimulationConfig":
        """Load a template from a JSON file."""
        # Import here to avoid circular imports
        from generation.config_schema import SimulationConfig

        with open(path, "r") as f:
            data = json.load(f)

        return SimulationConfig(**data)

    def _load_legacy_template(self, template_id: str) -> "SimulationConfig":
        """Load a template from legacy Python class method."""
        # Import here to avoid circular imports
        from generation.config_schema import SimulationConfig

        # Map template_id to class method
        method_name = self._template_id_to_method(template_id)

        if hasattr(SimulationConfig, method_name):
            method = getattr(SimulationConfig, method_name)
            return method()

        # Try the from_template method
        legacy_name = template_id.split("/")[-1]
        try:
            return SimulationConfig.from_template(legacy_name)
        except Exception:
            pass

        raise FileNotFoundError(f"Template not found: {template_id}")

    def _template_id_to_method(self, template_id: str) -> str:
        """Convert template ID to class method name."""
        # e.g., "showcase/board_meeting" -> "example_board_meeting"
        # e.g., "core/m01_heterogeneous_fidelity" -> "example_m01_heterogeneous_fidelity"
        name = template_id.split("/")[-1]
        return f"example_{name}"

    def get_coverage_matrix(self) -> Dict[str, Set[str]]:
        """
        Get the mechanism coverage matrix.

        Returns:
            Dict mapping mechanism ID to set of template IDs that test it
        """
        self._ensure_catalog_loaded()

        matrix: Dict[str, Set[str]] = {f"M{i}": set() for i in range(1, 19)}

        for template_id, info in self._catalog.templates.items():
            for mechanism in info.mechanisms:
                if mechanism in matrix:
                    matrix[mechanism].add(template_id)

        return matrix

    def get_mechanism_coverage_report(self) -> str:
        """
        Generate a human-readable mechanism coverage report.

        Returns:
            Formatted string showing which mechanisms have templates
        """
        self._ensure_catalog_loaded()
        matrix = self.get_coverage_matrix()

        lines = ["Mechanism Coverage Report", "=" * 50]

        for mechanism in sorted(matrix.keys(), key=lambda m: int(m[1:])):
            templates = matrix[mechanism]
            desc = self._catalog.mechanisms.get(mechanism, "Unknown")
            count = len(templates)
            status = "COVERED" if count > 0 else "MISSING"
            lines.append(f"{mechanism}: {status} ({count} templates)")
            if templates:
                for t in sorted(templates)[:3]:  # Show first 3
                    lines.append(f"    - {t}")
                if count > 3:
                    lines.append(f"    ... and {count - 3} more")

        return "\n".join(lines)

    def validate_template(self, template_id: str) -> ValidationResult:
        """
        Validate a template's JSON structure and configuration.

        Args:
            template_id: Template identifier

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check if template exists in catalog
        info = self.get_template_info(template_id)
        if info is None:
            errors.append(f"Template '{template_id}' not found in catalog")
            return ValidationResult(template_id, False, errors, warnings)

        # Try to load the template
        try:
            config = self.load_template(template_id)
        except FileNotFoundError as e:
            errors.append(f"Template file not found: {e}")
            return ValidationResult(template_id, False, errors, warnings)
        except Exception as e:
            errors.append(f"Failed to load template: {e}")
            return ValidationResult(template_id, False, errors, warnings)

        # Validate config structure
        if not config.scenario_description:
            errors.append("Missing scenario_description")
        if not config.world_id:
            errors.append("Missing world_id")

        # Validate entity count matches tier
        entity_count = config.entities.count
        tier_limits = {
            "quick": (1, 4),
            "standard": (3, 8),
            "comprehensive": (5, 12),
            "stress": (8, 100),
        }
        if info.tier.value in tier_limits:
            min_e, max_e = tier_limits[info.tier.value]
            if entity_count < min_e or entity_count > max_e:
                warnings.append(
                    f"Entity count {entity_count} outside expected range "
                    f"[{min_e}, {max_e}] for tier '{info.tier.value}'"
                )

        return ValidationResult(
            template_id=template_id,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_all_templates(self) -> Dict[str, ValidationResult]:
        """
        Validate all templates in the catalog.

        Returns:
            Dict mapping template_id to ValidationResult
        """
        self._ensure_catalog_loaded()

        results = {}
        for template_id in self._catalog.templates:
            results[template_id] = self.validate_template(template_id)

        return results

    def get_quick_test_suite(self) -> List[TemplateInfo]:
        """Get templates suitable for quick testing (< 1 min each)."""
        return self.list_templates(tier="quick", status="verified")

    def get_full_test_suite(self) -> List[TemplateInfo]:
        """Get all verified templates for comprehensive testing."""
        return self.list_templates(status="verified")

    def get_convergence_suite(self) -> List[TemplateInfo]:
        """Get convergence testing templates."""
        return self.list_templates(category="convergence")

    # =========================================================================
    # Patch Methods (SynthasAIzer paradigm)
    # =========================================================================

    def list_patch_categories(self) -> List[str]:
        """
        List all available patch categories.

        Returns:
            List of category names (e.g., ['corporate', 'historical', 'crisis', ...])
        """
        self._ensure_catalog_loaded()
        return list(self._catalog.patches.keys())

    def list_patches_by_category(self, category: str) -> List[str]:
        """
        List template IDs in a specific patch category.

        Args:
            category: Patch category (e.g., 'corporate', 'mystical')

        Returns:
            List of template IDs in that category
        """
        self._ensure_catalog_loaded()
        return self._catalog.patches.get(category, [])

    def get_patch_metadata(self, template_id: str) -> Optional[PatchInfo]:
        """
        Get patch metadata for a specific template.

        Args:
            template_id: Template identifier (e.g., "showcase/board_meeting")

        Returns:
            PatchInfo if template has patch metadata, None otherwise
        """
        try:
            # Load the template JSON directly to get patch metadata
            json_path = self._templates_dir / f"{template_id}.json"
            if not json_path.exists():
                # Try legacy path
                legacy_name = template_id.split("/")[-1]
                json_path = self._templates_dir / f"{legacy_name}.json"

            if not json_path.exists():
                return None

            with open(json_path, "r") as f:
                data = json.load(f)

            patch_data = data.get("patch")
            if patch_data is None:
                return None

            return PatchInfo(
                name=patch_data.get("name", ""),
                category=patch_data.get("category", ""),
                tags=patch_data.get("tags", []),
                author=patch_data.get("author", ""),
                version=patch_data.get("version", ""),
                description=patch_data.get("description", ""),
            )
        except Exception:
            return None

    def get_all_patches(self) -> Dict[str, PatchInfo]:
        """
        Get patch metadata for all templates that have it.

        Returns:
            Dict mapping template_id to PatchInfo
        """
        self._ensure_catalog_loaded()
        patches = {}
        for template_id in self._catalog.templates:
            patch_info = self.get_patch_metadata(template_id)
            if patch_info:
                patches[template_id] = patch_info
        return patches

    def get_patches_report(self) -> str:
        """
        Generate a human-readable patches report.

        Returns:
            Formatted string showing patches by category
        """
        self._ensure_catalog_loaded()
        lines = [
            "SynthasAIzer Patches Report",
            "=" * 50,
            "",
        ]

        for category in sorted(self._catalog.patches.keys()):
            template_ids = self._catalog.patches[category]
            lines.append(f"{category.upper()} ({len(template_ids)} patches)")
            lines.append("-" * 40)
            for template_id in template_ids:
                patch_info = self.get_patch_metadata(template_id)
                if patch_info:
                    lines.append(f"  {patch_info.name}")
                    lines.append(f"    Template: {template_id}")
                    lines.append(f"    {patch_info.description}")
                else:
                    lines.append(f"  {template_id} (no patch metadata)")
            lines.append("")

        return "\n".join(lines)


# Singleton instance for convenience
_loader: Optional[TemplateLoader] = None


def get_loader() -> TemplateLoader:
    """Get the singleton TemplateLoader instance."""
    global _loader
    if _loader is None:
        _loader = TemplateLoader()
    return _loader


def list_templates(
    tier: Optional[str] = None,
    category: Optional[str] = None,
    mechanism: Optional[str] = None,
) -> List[str]:
    """
    Convenience function to list template IDs.

    Returns list of template ID strings for use with load_template().
    """
    infos = get_loader().list_templates(tier=tier, category=category, mechanism=mechanism)
    return [info.id for info in infos]


def load_template(template_id: str) -> "SimulationConfig":
    """
    Convenience function to load a template.

    Args:
        template_id: Template identifier (e.g., "showcase/board_meeting")

    Returns:
        SimulationConfig instance
    """
    return get_loader().load_template(template_id)


def get_coverage_matrix() -> Dict[str, Set[str]]:
    """Convenience function to get mechanism coverage matrix."""
    return get_loader().get_coverage_matrix()
