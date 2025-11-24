#!/usr/bin/env python3
"""
conftest.py - Shared pytest configuration and fixtures for Timepoint-Daedalus

Provides:
- Common fixtures for all test types (unit/integration/system/e2e)
- Test validation and quality checks (from test_validation_system.py)
- Database and storage management
- LLM client configuration
- Async test support
- Test file tracking and timestamp monitoring
"""
import ast
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import test tracker for file monitoring
pytest_plugins = ['tests.pytest_test_tracker']


# ============================================================================
# Test Quality Validation (from test_validation_system.py)
# ============================================================================

@dataclass
class TestQualityReport:
    """Quality report for test validation"""
    file_path: str
    issues: List[str]
    warnings: List[str]
    quality_score: float


def validate_test_quality(item: pytest.Item) -> TestQualityReport:
    """Validate test quality using AST analysis"""
    critical_patterns = [
        (r'assert True\b', "Meaningless assertion 'assert True'"),
        (r'assert False\b(?!\s*,)', "Always-failing assertion 'assert False'"),
        (r'^\s*pass\s*$', "Empty test body with only 'pass'"),
        (r'raise NotImplementedError', "Placeholder implementation"),
        (r'time\.sleep\(\d+\)', "Unnecessary sleep() in test"),
    ]
    warning_patterns = [
        (r'print\(', "Debug print() statement"),
        (r'pdb\.set_trace', "Debug breakpoint left in code"),
        (r'# TODO', "Incomplete implementation (TODO)"),
        (r'except.*:\s*pass', "Bare except clause"),
    ]

    file_path = str(item.fspath)
    issues = []
    warnings = []
    quality_score = 1.0

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Check for critical patterns
        for pattern, message in critical_patterns:
            if re.search(pattern, content, re.MULTILINE):
                issues.append(f"{item.name}: {message}")
                quality_score -= 0.2

        # Check for warning patterns
        for pattern, message in warning_patterns:
            if re.search(pattern, content):
                warnings.append(f"{item.name}: {message}")
                quality_score -= 0.1

        quality_score = max(0.0, quality_score)

    except Exception as e:
        issues.append(f"Failed to analyze {file_path}: {e}")
        quality_score = 0.5

    return TestQualityReport(
        file_path=file_path,
        issues=issues,
        warnings=warnings,
        quality_score=quality_score
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add quality validation and auto-marking

    - Validates test quality and warns about issues
    - Auto-marks tests based on their characteristics
    - Skips low-quality tests if --strict-quality is set
    """
    strict_quality = config.getoption("--strict-quality", default=False)
    quality_threshold = float(config.getoption("--quality-threshold", default="0.7"))

    for item in items:
        # Validate test quality
        report = validate_test_quality(item)

        if report.issues and strict_quality:
            if report.quality_score < quality_threshold:
                item.add_marker(pytest.mark.skip(
                    reason=f"Quality score {report.quality_score:.2f} below threshold {quality_threshold}: {report.issues[0]}"
                ))

        # Auto-mark slow tests (those with sleep, LLM calls, etc.)
        if 'llm_client' in item.fixturenames or 'real_llm' in item.fixturenames:
            if not item.get_closest_marker('slow'):
                item.add_marker(pytest.mark.slow)
            if not item.get_closest_marker('llm'):
                item.add_marker(pytest.mark.llm)

        # Auto-mark integration tests (those using multiple fixtures)
        if len(item.fixturenames) >= 3 and not item.get_closest_marker('integration'):
            item.add_marker(pytest.mark.integration)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--strict-quality",
        action="store_true",
        default=False,
        help="Skip tests with quality score below threshold"
    )
    parser.addoption(
        "--quality-threshold",
        action="store",
        default="0.7",
        help="Minimum quality score (0.0-1.0) for tests to run"
    )
    parser.addoption(
        "--skip-llm",
        action="store_true",
        default=False,
        help="Skip tests that make real LLM API calls"
    )
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow-running tests"
    )
    parser.addoption(
        "--real-llm",
        action="store_true",
        default=False,
        help="Enable real LLM API calls (requires OPENROUTER_API_KEY)"
    )


def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    # Register all markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (multiple components)")
    config.addinivalue_line("markers", "system: System-level tests (full stack)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (complete workflows)")
    config.addinivalue_line("markers", "slow: Slow-running tests (>1 second)")
    config.addinivalue_line("markers", "llm: Tests making real LLM API calls")
    config.addinivalue_line("markers", "performance: Performance and benchmark tests")
    config.addinivalue_line("markers", "animism: Animistic entity functionality")
    config.addinivalue_line("markers", "temporal: Modal temporal causality")
    config.addinivalue_line("markers", "ai_entity: AI entity service components")
    config.addinivalue_line("markers", "validation: Data validation and consistency")
    config.addinivalue_line("markers", "safety: Security and safety features")
    config.addinivalue_line("markers", "compliance: Regulatory and compliance")
    config.addinivalue_line("markers", "validation_workflow: Critical validation workflow tests (requires real LLM)")

    # Apply skip markers based on options
    if config.getoption("--skip-llm"):
        config.addinivalue_line("markers", "llm: skip(reason='--skip-llm specified')")

    if config.getoption("--skip-slow"):
        config.addinivalue_line("markers", "slow: skip(reason='--skip-slow specified')")


# ============================================================================
# Shared Fixtures - Database and Storage
# ============================================================================

@pytest.fixture(scope="function")
def temp_db_path() -> Generator[str, None, None]:
    """Provide a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


@pytest.fixture(scope="function")
def graph_store(temp_db_path):
    """Provide a temporary GraphStore instance"""
    from storage import GraphStore

    store = GraphStore(f"sqlite:///{temp_db_path}")
    yield store

    # Cleanup happens via temp_db_path fixture


@pytest.fixture(scope="session")
def shared_graph_store():
    """Provide a session-scoped shared GraphStore for integration tests"""
    from storage import GraphStore

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = GraphStore(f"sqlite:///{db_path}")
    yield store

    # Cleanup
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================================================
# Shared Fixtures - LLM Clients
# ============================================================================

@pytest.fixture(scope="session")
def llm_api_key() -> Optional[str]:
    """Get LLM API key from environment"""
    return os.getenv('OPENROUTER_API_KEY')


@pytest.fixture(scope="session")
def has_llm_api_key(llm_api_key) -> bool:
    """Check if LLM API key is available"""
    return llm_api_key is not None and llm_api_key != 'test'


@pytest.fixture(scope="function")
def llm_client(llm_api_key, request):
    """
    Provide LLM client (mock or real based on configuration)

    - Uses mock by default
    - Uses real LLM if --real-llm flag is set and API key is available
    - Skips test if real LLM is required but API key is missing
    """
    from llm_v2 import LLMClient

    # Check if test requires real LLM
    requires_real = (
        request.config.getoption("--real-llm") or
        request.node.get_closest_marker('llm') is not None
    )

    if requires_real:
        if not llm_api_key or llm_api_key == 'test':
            pytest.skip("Real LLM test requires OPENROUTER_API_KEY")

        # Real LLM client
        client = LLMClient(api_key=llm_api_key)

        # Track costs
        start_time = time.time()
        yield client

        # Log execution time for cost tracking
        execution_time = time.time() - start_time
        if execution_time > 5:  # Log if took more than 5 seconds
            print(f"\n💰 LLM test '{request.node.name}' took {execution_time:.2f}s")
    else:
        # Mock LLM client - use dummy key
        client = LLMClient(api_key='test')
        yield client


@pytest.fixture(scope="function")
def real_llm_client(llm_api_key):
    """
    Force real LLM client (always requires API key)

    Use this fixture when you explicitly need real LLM calls
    """
    from llm_v2 import LLMClient

    if not llm_api_key or llm_api_key == 'test':
        pytest.skip("OPENROUTER_API_KEY not set - skipping real LLM test")

    return LLMClient(api_key=llm_api_key)


# ============================================================================
# Shared Fixtures - Common Test Data
# ============================================================================

@pytest.fixture(scope="session")
def sample_timepoint():
    """Provide a sample timepoint for testing"""
    from schemas import Timepoint, ResolutionLevel

    return Timepoint(
        timepoint_id="test_tp_001",
        timestamp=datetime(1789, 4, 30),
        event_description="Constitutional Convention",
        entities_present=["hamilton", "washington", "madison"],
        resolution_level=ResolutionLevel.TENSOR_ONLY
    )


@pytest.fixture(scope="function")
def sample_entity():
    """Provide a sample entity for testing"""
    from schemas import Entity, ResolutionLevel

    return Entity(
        entity_id="test_entity_001",
        entity_type="human",
        timepoint="test_tp_001",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        entity_metadata={"role": "test_subject"}
    )


@pytest.fixture(scope="function")
def sample_entities():
    """Provide multiple sample entities"""
    from schemas import Entity, ResolutionLevel

    return [
        Entity(
            entity_id=f"test_entity_{i:03d}",
            entity_type="human",
            timepoint="test_tp_001",
            resolution_level=ResolutionLevel.TENSOR_ONLY,
            entity_metadata={"role": f"test_subject_{i}"}
        )
        for i in range(1, 6)
    ]


# ============================================================================
# Shared Fixtures - Workflow and Service Components
# ============================================================================

@pytest.fixture(scope="function")
def temporal_agent(graph_store, llm_client):
    """Provide a TemporalAgent for testing"""
    from workflows import TemporalAgent

    return TemporalAgent(store=graph_store, llm_client=llm_client)


@pytest.fixture(scope="function")
def ai_entity_service(graph_store, llm_client):
    """Provide AIEntityService for testing"""
    from ai_entity_service import AIEntityService

    return AIEntityService(store=graph_store, llm_client=llm_client)


@pytest.fixture(scope="function")
def validator():
    """Provide a Validator instance"""
    from validation import Validator

    return Validator()


# ============================================================================
# Async Test Support
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Provide event loop for async tests"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Output and Reporting
# ============================================================================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Enhance test reports with additional information

    - Adds quality score to test report
    - Tracks test timing
    - Logs LLM usage
    """
    outcome = yield
    report = outcome.get_result()

    # Add quality score to report
    if call.when == "setup":
        quality_report = validate_test_quality(item)
        report.quality_score = quality_report.quality_score
        report.quality_issues = quality_report.issues
        report.quality_warnings = quality_report.warnings

    # Track LLM test execution
    if call.when == "call" and item.get_closest_marker('llm'):
        if report.passed:
            print(f"\n✅ LLM test passed: {item.name}")
        elif report.failed:
            print(f"\n❌ LLM test failed: {item.name}")


@pytest.fixture(scope="session", autouse=True)
def print_test_summary(request):
    """Print test execution summary at the end"""
    yield

    # Check for LLM cost logs
    log_dir = Path("logs/llm_calls")
    if log_dir.exists():
        import glob
        log_files = glob.glob(str(log_dir / "*.jsonl"))
        if log_files:
            print("\n" + "="*70)
            print("💰 LLM COST SUMMARY")
            print("="*70)
            print(f"Log files: {len(log_files)}")
            print(f"Location: {log_dir}")
            print("To calculate total cost:")
            print(f"  cat {log_dir}/*.jsonl | jq -s 'map(.cost_usd) | add'")
            print("="*70)
