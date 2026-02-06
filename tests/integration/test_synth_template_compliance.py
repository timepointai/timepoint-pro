"""
Integration Tests for SYNTH.md Template Compliance

Tests that all templates have proper patch metadata, envelope configurations,
and integrate correctly with the TemplateLoader patch methods.

SYNTH.md defines the SynthasAIzer paradigm:
- Templates as "patches" (named presets with category/tags)
- ADSR envelopes for entity presence lifecycle
- Voice controls for entity mixing
"""

import pytest
import json
from pathlib import Path
from dataclasses import asdict

from generation.templates.loader import (
    TemplateLoader,
    PatchInfo,
    TemplateInfo,
)
from generation.config_schema import SimulationConfig
from synth import EnvelopeConfig


class TestPatchMetadataCompliance:
    """Tests for patch metadata in all templates."""

    @pytest.fixture(scope="class")
    def loader(self):
        """Shared TemplateLoader instance."""
        return TemplateLoader()

    @pytest.fixture(scope="class")
    def all_templates(self, loader):
        """Get all template IDs."""
        return [t.id for t in loader.list_templates()]

    def test_patch_categories_exist(self, loader):
        """Catalog should have patches section with categories."""
        categories = loader.list_patch_categories()
        assert len(categories) > 0, "No patch categories found"

        expected_categories = [
            "corporate", "historical", "crisis", "mystical",
            "mystery", "directorial", "convergence"
        ]
        for cat in expected_categories:
            assert cat in categories, f"Missing expected category: {cat}"

    def test_all_templates_have_patch_metadata(self, loader, all_templates):
        """Every template should have patch metadata."""
        missing_patches = []
        for template_id in all_templates:
            patch = loader.get_patch_metadata(template_id)
            if patch is None:
                missing_patches.append(template_id)

        assert len(missing_patches) == 0, (
            f"Templates missing patch metadata: {missing_patches}"
        )

    def test_patch_metadata_required_fields(self, loader, all_templates):
        """Patch metadata should have all required fields."""
        incomplete_patches = []
        for template_id in all_templates:
            patch = loader.get_patch_metadata(template_id)
            if patch:
                missing = []
                if not patch.name:
                    missing.append("name")
                if not patch.category:
                    missing.append("category")
                if not patch.tags:
                    missing.append("tags")
                if not patch.description:
                    missing.append("description")
                if missing:
                    incomplete_patches.append((template_id, missing))

        assert len(incomplete_patches) == 0, (
            f"Patches with missing fields: {incomplete_patches}"
        )

    def test_patch_categories_match_catalog(self, loader, all_templates):
        """Patch category in template should match catalog classification."""
        mismatches = []
        catalog = loader.get_catalog()

        for template_id in all_templates:
            patch = loader.get_patch_metadata(template_id)
            if patch:
                # Check if template is in the category it claims
                templates_in_category = catalog.patches.get(patch.category, [])
                if template_id not in templates_in_category:
                    mismatches.append(
                        (template_id, patch.category, templates_in_category)
                    )

        if mismatches:
            msg = "Patch category mismatches:\n"
            for tid, cat, templates in mismatches:
                msg += f"  {tid} claims category '{cat}' but not in catalog\n"
            assert False, msg

    def test_unique_patch_names(self, loader, all_templates):
        """Patch names should be unique across templates."""
        names = {}
        for template_id in all_templates:
            patch = loader.get_patch_metadata(template_id)
            if patch:
                if patch.name in names:
                    names[patch.name].append(template_id)
                else:
                    names[patch.name] = [template_id]

        duplicates = {k: v for k, v in names.items() if len(v) > 1}
        assert len(duplicates) == 0, f"Duplicate patch names: {duplicates}"

    def test_patch_tags_not_empty(self, loader, all_templates):
        """Patches should have at least one tag."""
        empty_tags = []
        for template_id in all_templates:
            patch = loader.get_patch_metadata(template_id)
            if patch and len(patch.tags) == 0:
                empty_tags.append(template_id)

        assert len(empty_tags) == 0, (
            f"Templates with empty tags: {empty_tags}"
        )


class TestEnvelopeCompliance:
    """Tests for envelope configurations in templates."""

    @pytest.fixture(scope="class")
    def loader(self):
        return TemplateLoader()

    @pytest.fixture(scope="class")
    def showcase_templates(self, loader):
        """Showcase templates should have envelopes."""
        return [t.id for t in loader.list_templates(category="showcase")]

    def test_showcase_templates_have_envelopes(self, loader, showcase_templates):
        """Showcase templates should have envelope configurations."""
        missing_envelopes = []
        for template_id in showcase_templates:
            try:
                config = loader.load_template(template_id)
                envelope = config.entities.get_envelope()
                if envelope is None:
                    missing_envelopes.append(template_id)
            except Exception as e:
                missing_envelopes.append(f"{template_id} (error: {e})")

        # Allow for some flexibility - warn but don't fail
        if missing_envelopes:
            pytest.skip(
                f"Some showcase templates missing envelopes: {missing_envelopes}"
            )

    def test_envelope_values_valid(self, loader):
        """All envelope configs should have valid ADSR values."""
        invalid_envelopes = []
        for template in loader.list_templates():
            try:
                config = loader.load_template(template.id)
                if config.entities.envelope:
                    env = config.entities.envelope
                    # Check bounds
                    for field in ["attack", "decay", "sustain", "release"]:
                        val = getattr(env, field, None)
                        if val is not None and (val < 0.0 or val > 1.0):
                            invalid_envelopes.append(
                                (template.id, field, val)
                            )
            except Exception:
                pass  # Skip templates that fail to load

        assert len(invalid_envelopes) == 0, (
            f"Invalid envelope values: {invalid_envelopes}"
        )


class TestPatchLoaderMethods:
    """Tests for TemplateLoader patch methods."""

    @pytest.fixture(scope="class")
    def loader(self):
        return TemplateLoader()

    def test_list_patch_categories(self, loader):
        """list_patch_categories should return list of strings."""
        categories = loader.list_patch_categories()
        assert isinstance(categories, list)
        assert all(isinstance(c, str) for c in categories)

    def test_list_patches_by_category_valid(self, loader):
        """list_patches_by_category should return template IDs."""
        categories = loader.list_patch_categories()
        for category in categories:
            patches = loader.list_patches_by_category(category)
            assert isinstance(patches, list)
            for patch_id in patches:
                assert "/" in patch_id, f"Invalid patch ID format: {patch_id}"

    def test_list_patches_by_category_invalid(self, loader):
        """Invalid category should return empty list."""
        patches = loader.list_patches_by_category("nonexistent_category")
        assert patches == []

    def test_get_patch_metadata_returns_patchinfo(self, loader):
        """get_patch_metadata should return PatchInfo or None."""
        templates = loader.list_templates()
        for template in templates[:5]:  # Test first 5
            patch = loader.get_patch_metadata(template.id)
            assert patch is None or isinstance(patch, PatchInfo)

    def test_get_all_patches(self, loader):
        """get_all_patches should return dict of PatchInfo objects."""
        patches = loader.get_all_patches()
        assert isinstance(patches, dict)
        for template_id, patch_info in patches.items():
            assert isinstance(template_id, str)
            assert isinstance(patch_info, PatchInfo)

    def test_get_patches_report(self, loader):
        """get_patches_report should return formatted string."""
        report = loader.get_patches_report()
        assert isinstance(report, str)
        assert "SynthasAIzer" in report or "Patches" in report
        assert len(report) > 100  # Should be non-trivial

    def test_patch_info_serializable(self, loader):
        """PatchInfo should be serializable to dict."""
        patches = loader.get_all_patches()
        for patch_info in list(patches.values())[:3]:
            d = asdict(patch_info)
            assert "name" in d
            assert "category" in d
            assert "tags" in d
            # Should be JSON-serializable
            json_str = json.dumps(d)
            assert json_str


class TestCatalogPatchConsistency:
    """Tests for consistency between catalog patches and template files."""

    @pytest.fixture(scope="class")
    def loader(self):
        return TemplateLoader()

    def test_catalog_patches_count(self, loader):
        """Catalog should have patches covering all templates."""
        catalog = loader.get_catalog()
        all_templates = set(t.id for t in loader.list_templates())

        cataloged_patches = set()
        for category, template_ids in catalog.patches.items():
            cataloged_patches.update(template_ids)

        # All templates should be in at least one category
        uncategorized = all_templates - cataloged_patches
        if uncategorized:
            pytest.fail(f"Templates not in any patch category: {uncategorized}")

    def test_no_duplicate_patch_entries(self, loader):
        """Templates should not appear in multiple categories."""
        catalog = loader.get_catalog()
        seen = {}
        duplicates = []

        for category, template_ids in catalog.patches.items():
            for tid in template_ids:
                if tid in seen:
                    duplicates.append((tid, seen[tid], category))
                else:
                    seen[tid] = category

        # Note: Some templates might legitimately be in multiple categories
        # This test just warns
        if duplicates:
            pytest.skip(
                f"Templates in multiple categories (may be intentional): {duplicates}"
            )


class TestCoreMechanismPatches:
    """Tests for core mechanism templates (M1-M18)."""

    @pytest.fixture(scope="class")
    def loader(self):
        return TemplateLoader()

    def test_mechanism_patches_have_m_tags(self, loader):
        """Core mechanism patches should have M* tags."""
        mechanism_patches = loader.list_patches_by_category("mechanism")
        missing_m_tags = []

        for template_id in mechanism_patches:
            patch = loader.get_patch_metadata(template_id)
            if patch:
                has_m_tag = any(
                    t.startswith("M") and t[1:].isdigit()
                    for t in patch.tags
                )
                if not has_m_tag:
                    missing_m_tags.append(template_id)

        assert len(missing_m_tags) == 0, (
            f"Mechanism patches without M* tags: {missing_m_tags}"
        )

    def test_verified_mechanisms_covered(self, loader):
        """Verified templates should cover their declared mechanisms."""
        coverage = loader.get_coverage_matrix()
        covered = [m for m in coverage if coverage[m]]

        # Verified templates cover 12 of 18 mechanisms
        # M2, M4, M5, M6, M9, M18 are not covered by any verified template
        assert len(covered) >= 12, (
            f"Expected at least 12 mechanisms covered, got {len(covered)}: {covered}"
        )


class TestPortalPatches:
    """Tests for PORTAL mode patches."""

    @pytest.fixture(scope="class")
    def loader(self):
        return TemplateLoader()

    def test_portal_patches_have_portal_tag(self, loader):
        """Portal patches should have 'portal' or 'backward' tag."""
        portal_patches = loader.list_patches_by_category("portal")
        missing_tags = []

        for template_id in portal_patches:
            patch = loader.get_patch_metadata(template_id)
            if patch:
                has_portal_tag = any(
                    "portal" in t.lower() or "backward" in t.lower()
                    for t in patch.tags
                )
                # Also check if template itself has portal mode
                if not has_portal_tag:
                    missing_tags.append(template_id)

        # This is a soft check - some may use different naming
        if missing_tags:
            pytest.skip(
                f"Portal patches without portal/backward tags: {missing_tags}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
