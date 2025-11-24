#!/usr/bin/env python3
"""
Test Rig - Lightweight monitor for Full E2E Timepoint workflows

This is a DUMB monitor - it just runs tests and tracks them.
All intelligence lives in the app (workflows/e2e_runner.py, metadata/, etc).

Prebaked Templates (all 5 causal modes, all 17 mechanisms):
- jefferson_dinner: Pearl mode, 7 timepoints, 3 entities [quick test]
- board_meeting: Pearl mode, 5 timepoints, 5 entities [quick test]
- scarlet_study_deep: Pearl mode, 101 timepoints, 5 entities, all M1-M17 [full test]
- empty_house_flashback: Nonlinear mode, 81 timepoints, 4 entities
- final_problem_branching: Branching mode, 61 timepoints, 4 entities
- hound_shadow_directorial: Directorial mode, 15 timepoints, 5 entities
- sign_loops_cyclical: Cyclical mode, 12 timepoints, 4 entities

Usage:
    python3 test_rig.py run --template jefferson_dinner
    python3 test_rig.py run-all                          # Run all templates & generate coverage matrix
    python3 test_rig.py list
    python3 test_rig.py status --test-id test_0001
    python3 test_rig.py kill --test-id test_0001
    python3 test_rig.py coverage                         # Show coverage matrix from completed runs
"""

import subprocess
import time
import json
import os
import signal
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Prebaked template definitions - now matching ResilientE2EWorkflowRunner
TEMPLATES = {
    "jefferson_dinner": {
        "name": "Jefferson's Compromise Dinner",
        "description": "Historical negotiation scenario (QUICK TEST)",
        "mode": "pearl",
        "entities": 3,
        "timepoints": 7,
        "mechanisms": [1, 2, 3, 4, 7, 8, 14],
        "expected_examples": 21,
        "cost_estimate": "$0.10-0.50",
        "runtime_estimate": "2-5min"
    },
    "board_meeting": {
        "name": "Tech Startup Board Meeting",
        "description": "Corporate scenario with acquisition proposal (QUICK TEST)",
        "mode": "pearl",
        "entities": 5,
        "timepoints": 5,
        "mechanisms": [1, 2, 3, 4, 7, 8],
        "expected_examples": 25,
        "cost_estimate": "$0.10-0.50",
        "runtime_estimate": "2-5min"
    },
    "scarlet_study_deep": {
        "name": "The Scarlet Study (Deep)",
        "description": "Detective investigation with all 17 mechanisms (FULL TEST)",
        "mode": "pearl",
        "entities": 5,
        "timepoints": 101,
        "mechanisms": list(range(1, 18)),  # M1-M17
        "expected_examples": 500,
        "cost_estimate": "$5-15",
        "runtime_estimate": "15-30min"
    },
    "empty_house_flashback": {
        "name": "The Empty House (Nonlinear)",
        "description": "Survival story with flashback structure",
        "mode": "nonlinear",
        "entities": 4,
        "timepoints": 81,
        "mechanisms": [1, 2, 3, 4, 7, 8, 9, 10, 13, 14, 15, 16, 17],
        "expected_examples": 320,
        "cost_estimate": "$3-8",
        "runtime_estimate": "10-20min"
    },
    "final_problem_branching": {
        "name": "The Final Problem (Branching)",
        "description": "Counterfactual reasoning across timeline branches",
        "mode": "branching",
        "entities": 4,
        "timepoints": 61,
        "mechanisms": [1, 2, 3, 5, 6, 7, 8, 11, 12, 14, 15, 16, 17],
        "expected_examples": 240,
        "cost_estimate": "$2-6",
        "runtime_estimate": "8-15min"
    },
    "hound_shadow_directorial": {
        "name": "The Hound's Shadow (Directorial)",
        "description": "Detective noir with narrative arc structure",
        "mode": "directorial",
        "entities": 5,
        "timepoints": 15,
        "mechanisms": [1, 2, 3, 4, 7, 8, 10, 11, 13, 14, 15, 16, 17],
        "expected_examples": 70,
        "cost_estimate": "$0.50-2",
        "runtime_estimate": "5-10min"
    },
    "sign_loops_cyclical": {
        "name": "The Sign of Four Loops (Cyclical)",
        "description": "Time loop with prophecy mechanics",
        "mode": "cyclical",
        "entities": 4,
        "timepoints": 12,
        "mechanisms": [1, 2, 3, 4, 7, 8, 13, 14, 15, 16, 17],
        "expected_examples": 44,
        "cost_estimate": "$0.50-2",
        "runtime_estimate": "3-8min"
    }
}


class TestRig:
    """Simple test monitor - runs ResilientE2EWorkflowRunner and tracks results"""

    def __init__(self, workspace_dir: str = "."):
        self.workspace = Path(workspace_dir)
        self.registry_file = self.workspace / "test_registry.json"
        self.log_dir = self.workspace / "logs" / "test_runs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.tests = self._load_registry()

    def _load_registry(self) -> Dict:
        """Load test registry"""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {"tests": {}, "next_id": 1}

    def _save_registry(self):
        """Save test registry"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.tests, f, indent=2, default=str)

    def list_templates(self):
        """List available prebaked templates"""
        print("="*80)
        print("AVAILABLE PREBAKED TEMPLATES")
        print("="*80)
        print("\nCoverage: 5/5 causal modes | 17/17 mechanisms")
        print("\nQUICK TESTS (< 5min):")
        for template_id in ["jefferson_dinner", "board_meeting"]:
            info = TEMPLATES[template_id]
            print(f"\n  📋 {template_id}")
            print(f"     {info['description']}")
            print(f"     {info['mode']} | {info['entities']} entities | {info['timepoints']} timepoints")
            print(f"     Cost: {info['cost_estimate']}, Runtime: {info['runtime_estimate']}")

        print("\nFULL TESTS:")
        for template_id in ["scarlet_study_deep", "empty_house_flashback", "final_problem_branching",
                           "hound_shadow_directorial", "sign_loops_cyclical"]:
            info = TEMPLATES[template_id]
            print(f"\n  📋 {template_id}")
            print(f"     {info['description']}")
            print(f"     {info['mode']} | {info['entities']} entities | {info['timepoints']} timepoints")
            print(f"     Mechanisms: M{', M'.join(map(str, info['mechanisms']))}")
            print(f"     Cost: {info['cost_estimate']}, Runtime: {info['runtime_estimate']}")

    def run_template(self, template_id: str) -> str:
        """Run a prebaked template using ResilientE2EWorkflowRunner"""
        if template_id not in TEMPLATES:
            print(f"❌ Unknown template: {template_id}")
            print(f"Available: {', '.join(TEMPLATES.keys())}")
            return None

        template = TEMPLATES[template_id]
        test_id = f"test_{self.tests['next_id']:04d}"
        self.tests['next_id'] += 1

        log_file = self.log_dir / f"{test_id}_{template_id}.log"

        print(f"🚀 Starting {test_id}: {template['name']}")
        print(f"📋 Template: {template_id}")
        print(f"📝 Log: {log_file}")

        # Write Python code using ResilientE2EWorkflowRunner
        script_file = self.log_dir / f"{test_id}_{template_id}.py"
        python_code = f'''
import os
from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager
import logging

logging.basicConfig(level=logging.INFO)

# Load template
config = SimulationConfig.example_{template_id}()

print("\\n" + "="*80)
print(f"RUNNING RESILIENT E2E WORKFLOW: {{config.world_id}}")
print(f"6-Step Pipeline with Fault Tolerance: scene → temporal → training → format → oxen → metadata")
print("="*80 + "\\n")

try:
    # Initialize metadata manager
    metadata_manager = MetadataManager("metadata/runs.db")

    # Initialize Resilient E2E runner
    runner = ResilientE2EWorkflowRunner(metadata_manager)

    # Run complete workflow
    metadata = runner.run(config)

    print(f"\\n✅ E2E WORKFLOW COMPLETE")
    print(f"   Run ID: {{metadata.run_id}}")
    print(f"   Entities: {{metadata.entities_created}}")
    print(f"   Timepoints: {{metadata.timepoints_created}}")
    print(f"   Training Examples: {{metadata.training_examples}}")
    print(f"   Mechanisms Used: {{len(metadata.mechanisms_used)}}/17")
    print(f"   Cost: ${{metadata.cost_usd:.2f}}")
    if metadata.oxen_repo_url:
        print(f"   Oxen Repo: {{metadata.oxen_repo_url}}")

except Exception as e:
    print(f"\\n❌ E2E WORKFLOW FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    raise
'''

        with open(script_file, 'w') as f:
            f.write(python_code)

        # Build environment dict
        env = os.environ.copy()

        # Read .env file for API keys
        if (self.workspace / ".env").exists():
            with open(self.workspace / ".env") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip()

        # Map OXEN_API_KEY to OXEN_API_TOKEN if needed
        if 'OXEN_API_KEY' in env and 'OXEN_API_TOKEN' not in env:
            env['OXEN_API_TOKEN'] = env['OXEN_API_KEY']

        # Always enable LLM service for tests
        env['LLM_SERVICE_ENABLED'] = 'true'

        # Add workspace to PYTHONPATH
        env['PYTHONPATH'] = str(self.workspace)

        # Build bash command with venv activation
        bash_cmd = f"source .venv/bin/activate && python3 {script_file}"
        cmd = ["bash", "-c", bash_cmd]

        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=self.workspace,
                env=env,
                preexec_fn=os.setsid
            )

        # Register test
        self.tests["tests"][test_id] = {
            "id": test_id,
            "template": template_id,
            "template_info": template,
            "pid": process.pid,
            "log_file": str(log_file),
            "script_file": str(script_file),
            "status": "running",
            "started_at": datetime.now().isoformat(),
        }
        self._save_registry()

        print(f"✅ Test {test_id} started (PID: {process.pid})")
        print(f"\n📊 Monitor: python3 test_rig.py status --test-id {test_id}")
        print(f"📊 List all: python3 test_rig.py list")
        print(f"🛑 Kill: python3 test_rig.py kill --test-id {test_id}")
        return test_id

    def run_all_templates(self):
        """Run all templates and generate coverage matrix"""
        print("="*80)
        print("RUNNING ALL TEMPLATES")
        print("="*80)
        print(f"\nTotal templates: {len(TEMPLATES)}")
        print("This will run FULL E2E workflows for all 7 templates.")
        print("Estimated total runtime: 40-80 minutes")
        print("Estimated total cost: $10-30")
        print("\nTemplates:")
        for template_id in TEMPLATES:
            print(f"  - {template_id} ({TEMPLATES[template_id]['runtime_estimate']})")

        response = input("\nContinue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

        test_ids = []
        for template_id in TEMPLATES:
            print(f"\n{'='*80}")
            test_id = self.run_template(template_id)
            if test_id:
                test_ids.append(test_id)
            time.sleep(2)  # Brief pause between launches

        print(f"\n{'='*80}")
        print(f"✅ Launched {len(test_ids)} tests")
        print("="*80)
        print("\n📊 Monitor progress:")
        print("   python3 test_rig.py list")
        print("\n📊 Generate coverage matrix when all complete:")
        print("   python3 test_rig.py coverage")

    def show_coverage(self):
        """Show coverage matrix from completed runs"""
        print("="*80)
        print("COVERAGE MATRIX")
        print("="*80)

        # Import metadata components
        try:
            from metadata.run_tracker import MetadataManager
            from metadata.coverage_matrix import CoverageMatrix
        except ImportError as e:
            print(f"❌ Failed to import metadata: {e}")
            return

        # Load metadata
        metadata_manager = MetadataManager("metadata/runs.db")
        all_runs = metadata_manager.get_all_runs()

        if not all_runs:
            print("\n⚠️  No completed runs found. Run templates first:")
            print("   python3 test_rig.py run-all")
            return

        print(f"\nTotal runs: {len(all_runs)}")
        print(f"Completed: {sum(1 for r in all_runs if r.status == 'completed')}")
        print(f"Failed: {sum(1 for r in all_runs if r.status == 'failed')}")
        print("")

        # Generate matrices
        matrix = CoverageMatrix()

        # Generate text report
        report = matrix.generate_text_report(all_runs)
        print(report)

        # Save markdown report
        markdown = matrix.generate_markdown_report(all_runs)
        report_file = self.workspace / "COVERAGE_REPORT.md"
        with open(report_file, 'w') as f:
            f.write(markdown)

        print(f"\n📄 Markdown report saved: {report_file}")

    def check_status(self, test_id: str) -> Dict:
        """Check test status"""
        if test_id not in self.tests["tests"]:
            return {"error": f"Test {test_id} not found"}

        test = self.tests["tests"][test_id]

        # Check if process still running
        is_running = self._is_process_running(test["pid"])

        # Parse log for progress
        progress = self._parse_log(test["log_file"])

        # Update status
        test["progress"] = progress
        if not is_running and test["status"] == "running":
            test["status"] = "completed" if progress.get("success") else "failed"
            test["completed_at"] = datetime.now().isoformat()

        self._save_registry()
        return test

    def _is_process_running(self, pid: int) -> bool:
        """Check if process is running"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _parse_log(self, log_file: str) -> Dict:
        """Parse log file for progress"""
        log_path = Path(log_file)
        if not log_path.exists():
            return {}

        progress = {
            "log_size": log_path.stat().st_size,
            "last_modified": datetime.fromtimestamp(log_path.stat().st_mtime).isoformat(),
            "success": False,
            "errors": [],
            "current_step": None
        }

        try:
            with open(log_path) as f:
                lines = f.readlines()

                # Scan for E2E workflow steps
                for line in lines[-100:]:  # Last 100 lines
                    if "E2E WORKFLOW COMPLETE" in line or "✅" in line:
                        progress["success"] = True
                    if "Step 1:" in line:
                        progress["current_step"] = "start_tracking"
                    elif "Step 2:" in line:
                        progress["current_step"] = "initial_scene"
                    elif "Step 3:" in line:
                        progress["current_step"] = "temporal_generation"
                    elif "Step 4:" in line:
                        progress["current_step"] = "entity_training"
                    elif "Step 5:" in line:
                        progress["current_step"] = "format_training_data"
                    elif "Step 6:" in line:
                        progress["current_step"] = "oxen_upload"
                    elif "Step 7:" in line:
                        progress["current_step"] = "complete_metadata"

                    if "ERROR" in line or "FAILED" in line or "❌" in line:
                        progress["errors"].append(line.strip())
        except:
            pass

        return progress

    def list_tests(self) -> List[Dict]:
        """List all tests"""
        tests = list(self.tests["tests"].values())
        tests.sort(key=lambda t: t.get("started_at", ""), reverse=True)

        # Update status for all
        for test in tests:
            self.check_status(test["id"])

        return tests

    def kill_test(self, test_id: str) -> bool:
        """Kill a running test"""
        if test_id not in self.tests["tests"]:
            print(f"❌ Test {test_id} not found")
            return False

        test = self.tests["tests"][test_id]

        if not self._is_process_running(test["pid"]):
            print(f"Test {test_id} is not running")
            return False

        try:
            os.killpg(os.getpgid(test["pid"]), signal.SIGTERM)
            time.sleep(2)
            if self._is_process_running(test["pid"]):
                os.killpg(os.getpgid(test["pid"]), signal.SIGKILL)

            test["status"] = "killed"
            test["completed_at"] = datetime.now().isoformat()
            self._save_registry()

            print(f"✅ Test {test_id} killed")
            return True
        except Exception as e:
            print(f"❌ Failed to kill: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Test Rig for Timepoint E2E workflows")
    subparsers = parser.add_subparsers(dest="command")

    # Templates command
    subparsers.add_parser("templates", help="List available templates")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a template")
    run_parser.add_argument("--template", required=True, choices=list(TEMPLATES.keys()))

    # Run-all command
    subparsers.add_parser("run-all", help="Run all templates and generate coverage matrix")

    # Coverage command
    subparsers.add_parser("coverage", help="Show coverage matrix from completed runs")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check test status")
    status_parser.add_argument("--test-id", required=True)

    # List command
    subparsers.add_parser("list", help="List all tests")

    # Kill command
    kill_parser = subparsers.add_parser("kill", help="Kill a test")
    kill_parser.add_argument("--test-id", required=True)

    args = parser.parse_args()

    rig = TestRig()

    if args.command == "templates":
        rig.list_templates()

    elif args.command == "run":
        rig.run_template(args.template)

    elif args.command == "run-all":
        rig.run_all_templates()

    elif args.command == "coverage":
        rig.show_coverage()

    elif args.command == "status":
        status = rig.check_status(args.test_id)
        if "error" in status:
            print(status["error"])
        else:
            print(f"\n{'='*80}")
            print(f"TEST STATUS: {status['id']}")
            print(f"{'='*80}")
            print(f"Template: {status['template']}")
            print(f"Status: {status['status']}")
            print(f"Started: {status['started_at']}")
            if status.get('completed_at'):
                print(f"Completed: {status['completed_at']}")

            progress = status.get('progress', {})
            if progress.get('current_step'):
                print(f"Current Step: {progress['current_step']}")
            if progress.get('success'):
                print(f"✅ Success!")
            if progress.get('errors'):
                print(f"⚠️  Errors: {len(progress['errors'])}")
                print("\nRecent errors:")
                for error in progress['errors'][-5:]:
                    print(f"  {error}")

            print(f"\n📝 Log file: {status['log_file']}")
            print(f"📝 Script: {status.get('script_file', 'N/A')}")

    elif args.command == "list":
        tests = rig.list_tests()
        if not tests:
            print("No tests found")
        else:
            print(f"\n{'='*80}")
            print(f"ALL TESTS ({len(tests)} total)")
            print(f"{'='*80}\n")
            for test in tests:
                template = test.get("template_info", {})
                status_icon = "✅" if test["status"] == "completed" else "❌" if test["status"] == "failed" else "🔄"

                print(f"{status_icon} {test['id']}: {template.get('name', test['template'])}")
                print(f"   Status: {test['status']} | Started: {test['started_at']}")

                progress = test.get('progress', {})
                if progress.get('current_step'):
                    print(f"   Step: {progress['current_step']}")
                if progress.get('errors'):
                    print(f"   ⚠️  {len(progress['errors'])} error(s)")
                print()

    elif args.command == "kill":
        rig.kill_test(args.test_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
