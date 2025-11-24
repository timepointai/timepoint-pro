#!/usr/bin/env python3
"""
Single Template Execution with Dashboard Integration

Run a single template by name and automatically generate dashboard URL.
"""
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional

from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager


def run_template(runner, config, name: str, expected_mechanisms: Set[str]) -> Dict:
    """Run a single template and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {name}")
    print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
    print(f"{'='*80}\n")

    try:
        result = runner.run(config)
        mechanisms = set(result.mechanisms_used) if result.mechanisms_used else set()

        # Track Oxen URLs and PDF locations
        oxen_repo_url = result.oxen_repo_url if hasattr(result, 'oxen_repo_url') else None
        oxen_dataset_url = result.oxen_dataset_url if hasattr(result, 'oxen_dataset_url') else None

        # Find PDF files in datasets/{world_id}/
        pdf_paths = []
        template_dataset_dir = Path("datasets") / config.world_id
        if template_dataset_dir.exists():
            pdf_paths = [str(p) for p in template_dataset_dir.glob("*.pdf")]

        success = {
            'success': True,
            'run_id': result.run_id,
            'entities': result.entities_created,
            'timepoints': result.timepoints_created,
            'mechanisms': mechanisms,
            'expected': expected_mechanisms,
            'cost': result.cost_usd or 0.0,
            'summary': result.summary if hasattr(result, 'summary') else None,
            'oxen_repo_url': oxen_repo_url,
            'oxen_dataset_url': oxen_dataset_url,
            'pdf_paths': pdf_paths
        }

        print(f"\n✅ Success: {name}")
        print(f"   Run ID: {result.run_id}")
        print(f"   Entities: {result.entities_created}, Timepoints: {result.timepoints_created}")
        print(f"   Mechanisms: {', '.join(sorted(mechanisms))}")
        print(f"   Cost: ${result.cost_usd:.2f}")
        if oxen_repo_url:
            print(f"   Oxen Repo: {oxen_repo_url}")
        if pdf_paths:
            print(f"   PDFs: {len(pdf_paths)} generated")

        return success

    except Exception as e:
        print(f"\n❌ Failed: {name}")
        print(f"   Error: {str(e)[:200]}")
        return {
            'success': False,
            'error': str(e),
            'mechanisms': set(),
            'expected': expected_mechanisms,
            'cost': 0.0,
            'summary': None
        }


def get_latest_run_id(db_path: str = "metadata/runs.db") -> Optional[str]:
    """Get the most recent run_id from the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        print(f"Warning: Could not query database for run_id: {e}")
        return None


def print_dashboard_url(run_id: str, port: int = 8888):
    """Print clickable dashboard URL for the run"""
    dashboard_url = f"http://localhost:{port}/index.html?run_id={run_id}"
    print(f"\n{'='*80}")
    print(f"📊 DASHBOARD INTEGRATION")
    print(f"{'='*80}")
    print(f"\n✅ Run completed successfully!")
    print(f"\n🔗 View in Dashboard:")
    print(f"   {dashboard_url}")
    print(f"\n💡 TIP: Start the dashboard with:")
    print(f"   cd dashboards && ./dashboard.sh")
    print(f"\n{'='*80}\n")


def build_template_lookup() -> Dict[str, tuple]:
    """Build lookup dictionary of all available templates"""

    # Quick mode: safe, fast templates
    quick_templates = [
        ("board_meeting", SimulationConfig.example_board_meeting(), {"M7"}),
        ("jefferson_dinner", SimulationConfig.example_jefferson_dinner(), {"M3", "M7"}),
        ("hospital_crisis", SimulationConfig.example_hospital_crisis(), {"M8", "M14"}),
        ("kami_shrine", SimulationConfig.example_kami_shrine(), {"M16"}),
        ("detective_prospection", SimulationConfig.example_detective_prospection(), {"M15"}),
        ("vc_pitch_pearl", SimulationConfig.example_vc_pitch_pearl(), {"M7", "M11", "M15"}),
        ("vc_pitch_roadshow", SimulationConfig.example_vc_pitch_roadshow(), {"M3", "M7", "M10", "M13"}),
    ]

    # Full mode: expensive, comprehensive templates
    full_templates = [
        ("empty_house_flashback", SimulationConfig.example_empty_house_flashback(), {"M17", "M13", "M8"}),
        ("final_problem_branching", SimulationConfig.example_final_problem_branching(), {"M12", "M17", "M15"}),
        ("hound_shadow_directorial", SimulationConfig.example_hound_shadow_directorial(), {"M17", "M10", "M14"}),
        ("sign_loops_cyclical", SimulationConfig.example_sign_loops_cyclical(), {"M17", "M15", "M3"}),
        ("vc_pitch_branching", SimulationConfig.example_vc_pitch_branching(), {"M12", "M15", "M8", "M17"}),
        ("vc_pitch_strategies", SimulationConfig.example_vc_pitch_strategies(), {"M12", "M10", "M15", "M17"}),
    ]

    # Timepoint Corporate Formation Analysis
    timepoint_corporate_templates = [
        ("timepoint_ipo_reverse", SimulationConfig.timepoint_ipo_reverse_engineering(), {"M12", "M15", "M7", "M13", "M11"}),
        ("timepoint_acquisition_scenarios", SimulationConfig.timepoint_acquisition_scenarios(), {"M12", "M15", "M11", "M8", "M7", "M13"}),
        ("timepoint_cofounder_configs", SimulationConfig.timepoint_cofounder_configurations(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_equity_incentives", SimulationConfig.timepoint_equity_performance_incentives(), {"M12", "M13", "M7", "M15", "M11", "M8"}),
        ("timepoint_formation_decisions", SimulationConfig.timepoint_critical_formation_decisions(), {"M12", "M7", "M15", "M11"}),
        ("timepoint_success_vs_failure", SimulationConfig.timepoint_success_vs_failure_paths(), {"M12", "M7", "M13", "M8", "M11", "M15"}),
        ("timepoint_launch_marketing", SimulationConfig.timepoint_launch_marketing_campaigns(), {"M3", "M10", "M14"}),
        ("timepoint_staffing_growth", SimulationConfig.timepoint_staffing_and_growth(), {"M3", "M10", "M14", "M15"}),
        ("timepoint_personality_archetypes", SimulationConfig.timepoint_founder_personality_archetypes(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_charismatic_founder", SimulationConfig.timepoint_charismatic_founder_archetype(), {"M12", "M13", "M8", "M11", "M7"}),
        ("timepoint_demanding_genius", SimulationConfig.timepoint_demanding_genius_archetype(), {"M12", "M13", "M8", "M7", "M15", "M11"}),
        ("timepoint_ai_pricing_war", SimulationConfig.timepoint_ai_pricing_war(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_capability_leapfrog", SimulationConfig.timepoint_ai_capability_leapfrog(), {"M12", "M9", "M10", "M13"}),
        ("timepoint_ai_business_model_evolution", SimulationConfig.timepoint_ai_business_model_evolution(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_regulatory_divergence", SimulationConfig.timepoint_ai_regulatory_divergence(), {"M12", "M7", "M13", "M14"}),
    ]

    # PORTAL mode templates
    portal_templates = [
        ("portal_presidential_election", SimulationConfig.portal_presidential_election(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn", SimulationConfig.portal_startup_unicorn(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure", SimulationConfig.portal_academic_tenure(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure", SimulationConfig.portal_startup_failure(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # PORTAL simulation-judged variants
    portal_templates_simjudged_quick = [
        ("portal_presidential_election_simjudged_quick", SimulationConfig.portal_presidential_election_simjudged_quick(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_quick", SimulationConfig.portal_startup_unicorn_simjudged_quick(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_quick", SimulationConfig.portal_academic_tenure_simjudged_quick(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_quick", SimulationConfig.portal_startup_failure_simjudged_quick(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    portal_templates_simjudged = [
        ("portal_presidential_election_simjudged", SimulationConfig.portal_presidential_election_simjudged(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged", SimulationConfig.portal_startup_unicorn_simjudged(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged", SimulationConfig.portal_academic_tenure_simjudged(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged", SimulationConfig.portal_startup_failure_simjudged(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    portal_templates_simjudged_thorough = [
        ("portal_presidential_election_simjudged_thorough", SimulationConfig.portal_presidential_election_simjudged_thorough(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_thorough", SimulationConfig.portal_startup_unicorn_simjudged_thorough(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_thorough", SimulationConfig.portal_academic_tenure_simjudged_thorough(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_thorough", SimulationConfig.portal_startup_failure_simjudged_thorough(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # PORTAL Timepoint templates
    portal_timepoint_templates = [
        ("portal_timepoint_unicorn", SimulationConfig.portal_timepoint_unicorn(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success", SimulationConfig.portal_timepoint_series_a_success(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit", SimulationConfig.portal_timepoint_product_market_fit(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption", SimulationConfig.portal_timepoint_enterprise_adoption(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition", SimulationConfig.portal_timepoint_founder_transition(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    portal_timepoint_templates_simjudged_quick = [
        ("portal_timepoint_unicorn_simjudged_quick", SimulationConfig.portal_timepoint_unicorn_simjudged_quick(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged_quick", SimulationConfig.portal_timepoint_series_a_success_simjudged_quick(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged_quick", SimulationConfig.portal_timepoint_product_market_fit_simjudged_quick(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged_quick", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged_quick(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged_quick", SimulationConfig.portal_timepoint_founder_transition_simjudged_quick(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    portal_timepoint_templates_simjudged = [
        ("portal_timepoint_unicorn_simjudged", SimulationConfig.portal_timepoint_unicorn_simjudged(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged", SimulationConfig.portal_timepoint_series_a_success_simjudged(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged", SimulationConfig.portal_timepoint_product_market_fit_simjudged(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged", SimulationConfig.portal_timepoint_founder_transition_simjudged(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    portal_timepoint_templates_simjudged_thorough = [
        ("portal_timepoint_unicorn_simjudged_thorough", SimulationConfig.portal_timepoint_unicorn_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged_thorough", SimulationConfig.portal_timepoint_series_a_success_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged_thorough", SimulationConfig.portal_timepoint_product_market_fit_simjudged_thorough(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged_thorough", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged_thorough", SimulationConfig.portal_timepoint_founder_transition_simjudged_thorough(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    # Combine all templates
    all_templates = (
        quick_templates + full_templates + timepoint_corporate_templates +
        portal_templates + portal_templates_simjudged_quick + portal_templates_simjudged + portal_templates_simjudged_thorough +
        portal_timepoint_templates + portal_timepoint_templates_simjudged_quick + portal_timepoint_templates_simjudged + portal_timepoint_templates_simjudged_thorough
    )

    # Build lookup dictionary
    template_lookup = {}
    for name, config, expected in all_templates:
        template_lookup[name] = (config, expected)

    return template_lookup


def run_single_template(template_name: str, skip_summaries: bool = False) -> bool:
    """
    Run a single template by name and show dashboard URL.

    Args:
        template_name: Name of the template to run
        skip_summaries: Whether to skip LLM-powered summaries

    Returns:
        True if successful, False otherwise
    """
    print("=" * 80)
    print(f"SINGLE TEMPLATE EXECUTION: {template_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Build template lookup
    template_lookup = build_template_lookup()

    # Check if template exists
    if template_name not in template_lookup:
        print(f"❌ ERROR: Template '{template_name}' not found")
        print(f"\n📋 Available templates ({len(template_lookup)}):")

        # Group templates by category for better readability
        categories = {
            'Quick': [],
            'Full': [],
            'Timepoint Corporate': [],
            'Portal': [],
            'Portal Timepoint': []
        }

        for name in sorted(template_lookup.keys()):
            if name.startswith('portal_timepoint'):
                categories['Portal Timepoint'].append(name)
            elif name.startswith('portal'):
                categories['Portal'].append(name)
            elif name.startswith('timepoint'):
                categories['Timepoint Corporate'].append(name)
            elif name in ['board_meeting', 'jefferson_dinner', 'hospital_crisis', 'kami_shrine', 'detective_prospection', 'vc_pitch_pearl', 'vc_pitch_roadshow']:
                categories['Quick'].append(name)
            else:
                categories['Full'].append(name)

        for category, templates in categories.items():
            if templates:
                print(f"\n  {category} ({len(templates)}):")
                for t in templates:
                    print(f"    - {t}")

        return False

    # Get template config
    config, expected_mechanisms = template_lookup[template_name]

    # Initialize
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    runner = ResilientE2EWorkflowRunner(metadata_manager, generate_summary=not skip_summaries)

    # Run template
    result = run_template(runner, config, template_name, expected_mechanisms)

    # Print dashboard URL if successful
    if result['success'] and result.get('run_id'):
        print_dashboard_url(result['run_id'])

    # Print summary
    print("\n" + "=" * 80)
    print("SINGLE TEMPLATE EXECUTION COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Template: {template_name}")
    print(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    if result['success']:
        print(f"Cost: ${result.get('cost', 0.0):.2f}")
    print("=" * 80)
    print()

    return result['success']


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python run_single_template.py <template_name>")
        sys.exit(1)

    template_name = sys.argv[1]
    success = run_single_template(template_name)
    sys.exit(0 if success else 1)
