# ============================================================================
# conftest.py - Pytest configuration and fixtures
# ============================================================================
import pytest
import logging
import os

from llm import LLMClient
from storage import GraphStore

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add custom command-line options for pytest"""
    parser.addoption(
        "--verbose-tests",
        action="store_true",
        default=False,
        help="Enable verbose logging during tests"
    )


@pytest.fixture(scope="session", autouse=True)
def configure_logging(request):
    """Configure logging based on --verbose-tests flag"""
    verbose = request.config.getoption("--verbose-tests")
    
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S',
            force=True
        )
        logger.info("=" * 80)
        logger.info("VERBOSE TEST MODE ENABLED")
        logger.info("=" * 80)
    else:
        logging.basicConfig(level=logging.WARNING, force=True)
    
    return verbose


@pytest.fixture
def verbose_mode(request):
    """Fixture to check if verbose mode is enabled"""
    return request.config.getoption("--verbose-tests")


@pytest.fixture
def llm_client():
    """LLM client fixture - uses real LLM if API key available, otherwise dry-run"""
    api_key = os.getenv('OPENROUTER_API_KEY')

    if api_key:
        print("🔥 USING REAL LLM CLIENT (API key detected)")
        return LLMClient(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            dry_run=False
        )
    else:
        print("🧪 USING DRY-RUN LLM CLIENT (no API key - set OPENROUTER_API_KEY for real calls)")
        return LLMClient(api_key="test", base_url="http://test", dry_run=True)


@pytest.fixture
def force_real_llm_client():
    """Force real LLM client for 100% coverage testing (requires OPENROUTER_API_KEY)"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY required for real LLM coverage testing")

    print("🎯 FORCING REAL LLM CLIENT FOR 100% COVERAGE")
    return LLMClient(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        dry_run=False
    )


@pytest.fixture
def llm_client_dry_run():
    """LLM client fixture with dry-run mode (always dry-run)"""
    return LLMClient(api_key="test", base_url="http://test", dry_run=True)


@pytest.fixture
def graph_store():
    """Graph store fixture"""
    return GraphStore("sqlite:///:memory:")
