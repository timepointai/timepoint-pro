"""
pytest_test_tracker.py - Track test file execution and timestamps

Add this to conftest.py to track which tests ran and when they were last modified.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import pytest


class TestTracker:
    """Track test execution and file metadata"""

    def __init__(self):
        self.test_files: Dict[str, dict] = {}
        self.execution_log: List[dict] = []
        self.start_time = None
        self.end_time = None

    def track_file(self, file_path: str, test_name: str, outcome: str):
        """Track a test file execution"""
        if not os.path.exists(file_path):
            return

        file_stat = os.stat(file_path)

        if file_path not in self.test_files:
            self.test_files[file_path] = {
                'path': file_path,
                'size': file_stat.st_size,
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'tests_run': [],
                'outcomes': {}
            }

        self.test_files[file_path]['tests_run'].append(test_name)

        if outcome not in self.test_files[file_path]['outcomes']:
            self.test_files[file_path]['outcomes'][outcome] = 0
        self.test_files[file_path]['outcomes'][outcome] += 1

    def generate_report(self) -> dict:
        """Generate execution report"""
        return {
            'execution': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
            },
            'files': self.test_files,
            'summary': {
                'total_files': len(self.test_files),
                'total_tests': sum(len(f['tests_run']) for f in self.test_files.values()),
                'files_by_outcome': self._get_files_by_outcome()
            }
        }

    def _get_files_by_outcome(self) -> dict:
        """Group files by their primary outcome"""
        by_outcome = {'passed': [], 'failed': [], 'skipped': [], 'error': []}

        for file_path, data in self.test_files.items():
            outcomes = data['outcomes']
            if outcomes.get('failed', 0) > 0 or outcomes.get('error', 0) > 0:
                by_outcome['failed'].append(file_path)
            elif outcomes.get('skipped', 0) > 0:
                by_outcome['skipped'].append(file_path)
            elif outcomes.get('passed', 0) > 0:
                by_outcome['passed'].append(file_path)

        return by_outcome


# Global tracker instance
tracker = TestTracker()


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Track session start"""
    tracker.start_time = datetime.now()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Track individual test results"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        file_path = str(item.fspath)
        test_name = item.nodeid
        outcome_status = report.outcome

        tracker.track_file(file_path, test_name, outcome_status)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Generate and save tracking report at session end"""
    tracker.end_time = datetime.now()

    # Generate report
    report = tracker.generate_report()

    # Save to file
    report_dir = Path("logs/test_tracking")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"test_execution_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "="*70)
    print("📊 TEST EXECUTION TRACKING")
    print("="*70)
    print(f"Execution Time: {report['execution']['duration_seconds']:.2f}s")
    print(f"Files Tested: {report['summary']['total_files']}")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print()

    # Show files with failures
    failed_files = report['summary']['files_by_outcome']['failed']
    if failed_files:
        print("❌ Files with failures:")
        for file_path in failed_files:
            file_data = report['files'][file_path]
            print(f"  • {Path(file_path).name}")
            print(f"    Modified: {file_data['modified']}")
            print(f"    Outcomes: {file_data['outcomes']}")

    # Show passed files
    passed_files = report['summary']['files_by_outcome']['passed']
    if passed_files:
        print()
        print("✅ Files passed:")
        for file_path in passed_files:
            file_data = report['files'][file_path]
            print(f"  • {Path(file_path).name} ({len(file_data['tests_run'])} tests)")
            print(f"    Modified: {file_data['modified']}")

    print()
    print(f"📄 Full report: {report_file}")
    print("="*70)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add file tracking info to terminal summary"""
    terminalreporter.write_sep("=", "Test File Tracking")

    for file_path, data in sorted(tracker.test_files.items()):
        file_name = Path(file_path).name
        terminalreporter.write_line(f"\n{file_name}:")
        terminalreporter.write_line(f"  Last Modified: {data['modified']}")
        terminalreporter.write_line(f"  Tests Run: {len(data['tests_run'])}")
        terminalreporter.write_line(f"  Outcomes: {data['outcomes']}")
