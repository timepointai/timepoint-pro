#!/usr/bin/env python3
"""
Test Rig - Simple orchestrator for prebaked Timepoint scenarios

This is a DUMB orchestrator - it just runs tests and monitors them.
All intelligence lives in the app (orchestrator.py, workflows, etc).

Prebaked Templates (all 17 mechanisms):
- scarlet_study_deep: Pearl mode, 101 timepoints, 5 entities, all M1-M17
- empty_house_flashback: Nonlinear mode, 81 timepoints, 4 entities
- final_problem_branching: Branching mode, 61 timepoints × 4 branches, 4 entities
- jefferson_dinner: Historical, 7 timepoints, 3 entities
- board_meeting: Corporate, 5 timepoints, 5 entities

Usage:
    python3 test_rig.py run --template scarlet_study_deep
    python3 test_rig.py list
    python3 test_rig.py status --test-id test_0001
    python3 test_rig.py kill --test-id test_0001
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


# Prebaked template definitions
TEMPLATES = {
    "scarlet_study_deep": {
        "name": "The Scarlet Study (Deep)",
        "description": "Detective investigation with all 17 mechanisms",
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
        "description": "Counterfactual reasoning across 4 timeline branches",
        "mode": "branching",
        "entities": 4,
        "timepoints": 61,
        "branches": 4,
        "mechanisms": [1, 2, 3, 5, 6, 7, 8, 11, 12, 14, 15, 16, 17],
        "expected_examples": 240,
        "cost_estimate": "$2-6",
        "runtime_estimate": "8-15min"
    },
    "jefferson_dinner": {
        "name": "Jefferson's Compromise Dinner",
        "description": "Historical negotiation scenario",
        "mode": "pearl",
        "entities": 3,
        "timepoints": 7,
        "mechanisms": [1, 2, 3, 4, 7, 8, 14],
        "expected_examples": 21,
        "cost_estimate": "$0.10-0.50",
        "runtime_estimate": "1-2min"
    },
    "board_meeting": {
        "name": "Tech Startup Board Meeting",
        "description": "Corporate scenario with acquisition proposal",
        "mode": "pearl",
        "entities": 5,
        "timepoints": 5,
        "mechanisms": [1, 2, 3, 4, 7, 8],
        "expected_examples": 25,
        "cost_estimate": "$0.10-0.50",
        "runtime_estimate": "1-2min"
    }
}


class TestRig:
    """Simple test orchestrator - just runs and monitors"""

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
        for template_id, info in TEMPLATES.items():
            print(f"\n📋 {template_id}")
            print(f"   Name: {info['name']}")
            print(f"   {info['description']}")
            print(f"   Mode: {info['mode']}, Entities: {info['entities']}, Timepoints: {info['timepoints']}")
            if 'branches' in info:
                print(f"   Branches: {info['branches']}")
            print(f"   Mechanisms: M{', M'.join(map(str, info['mechanisms']))}")
            print(f"   Expected Examples: {info['expected_examples']}")
            print(f"   Cost: {info['cost_estimate']}, Runtime: {info['runtime_estimate']}")

    def run_template(self, template_id: str) -> str:
        """Run a prebaked template"""
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

        # Write Python code to temporary script file
        script_file = self.log_dir / f"{test_id}_{template_id}.py"
        python_code = f'''
import os
import tempfile
from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
import logging

logging.basicConfig(level=logging.INFO)

# Load template
config = SimulationConfig.example_{template_id}()

print("\\n" + "="*80)
print(f"RUNNING: {{config.world_id}}")
print("="*80 + "\\n")

try:
    # Initialize LLM client
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key, dry_run=False)

    # Initialize storage
    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{{db_path}}")

    # Run simulation
    result = simulate_event(
        config.scenario_description,
        llm,
        store,
        context={{
            "max_entities": config.entities.count,
            "max_timepoints": config.timepoints.count,
            "temporal_mode": config.temporal.mode.value
        }},
        save_to_db=True
    )

    print(f"\\n✅ COMPLETE: {{config.world_id}}")
    print(f"   Entities: {{len(result['entities'])}}")
    print(f"   Timepoints: {{len(result['timepoints'])}}")

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

except Exception as e:
    print(f"\\n❌ FAILED: {{e}}")
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

        # Add workspace to PYTHONPATH so imports work
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
            "status": "running",
            "started_at": datetime.now().isoformat(),
        }
        self._save_registry()

        print(f"✅ Test {test_id} started (PID: {process.pid})")
        print(f"\n📊 Monitor: python3 test_rig.py status --test-id {test_id}")
        print(f"📊 List all: python3 test_rig.py list")
        return test_id

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
            "errors": []
        }

        try:
            with open(log_path) as f:
                lines = f.readlines()
                for line in lines[-50:]:  # Last 50 lines
                    if "✅ COMPLETE" in line or "TEST PASSED" in line:
                        progress["success"] = True
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
    parser = argparse.ArgumentParser(description="Test Rig for Timepoint scenarios")
    subparsers = parser.add_subparsers(dest="command")

    # Templates command
    subparsers.add_parser("templates", help="List available templates")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a template")
    run_parser.add_argument("--template", required=True, choices=list(TEMPLATES.keys()))

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

    elif args.command == "status":
        status = rig.check_status(args.test_id)
        print(json.dumps(status, indent=2, default=str))

    elif args.command == "list":
        tests = rig.list_tests()
        if not tests:
            print("No tests found")
        else:
            print(f"Found {len(tests)} test(s):\n")
            for test in tests:
                template = test.get("template_info", {})
                print(f"{'='*80}")
                print(f"🧪 {test['id']}: {template.get('name', test['template'])}")
                print(f"{'='*80}")
                print(f"Status: {test['status']}")
                print(f"Template: {test['template']}")
                print(f"Started: {test['started_at']}")
                if test.get('completed_at'):
                    print(f"Completed: {test['completed_at']}")

                progress = test.get('progress', {})
                if progress.get('success'):
                    print(f"✅ Success!")
                if progress.get('errors'):
                    print(f"⚠️  Errors: {len(progress['errors'])}")
                print()

    elif args.command == "kill":
        rig.kill_test(args.test_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
