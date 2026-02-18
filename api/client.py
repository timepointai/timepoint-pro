"""
Timepoint Pro API Client SDK.

Python client for submitting simulations and batches via the REST API.
Provides a convenient interface for the batch submission and usage quota APIs.

Phase 6: Public API - Client SDK

Usage:
    from api.client import TimePointClient

    client = TimePointClient(api_key="your-api-key")

    # Submit a batch
    batch = client.submit_batch([
        {"template_id": "board_meeting", "entity_count": 4, "timepoint_count": 5},
        {"template_id": "hospital_crisis", "entity_count": 3, "timepoint_count": 4},
    ])

    # Check status
    status = client.get_batch_status(batch.batch_id)

    # Wait for completion
    result = client.wait_for_batch(batch.batch_id)

    # Check usage
    usage = client.get_usage()
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SimulationRequest:
    """Request to create a single simulation."""
    template_id: str
    entity_count: int = 3
    timepoint_count: int = 5
    custom_scenario: Optional[str] = None
    custom_entities: Optional[List[Dict[str, Any]]] = None
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class BatchRequest:
    """Request to create a batch of simulations."""
    simulations: List[SimulationRequest]
    budget_cap_usd: Optional[float] = None
    priority: str = "normal"  # "low", "normal", "high"
    fail_fast: bool = False
    parallel_jobs: int = 4
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BatchProgress:
    """Progress information for a batch."""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    progress_percent: float


@dataclass
class BatchCost:
    """Cost information for a batch."""
    estimated_cost_usd: float
    actual_cost_usd: float
    budget_cap_usd: Optional[float]
    budget_remaining_usd: Optional[float]
    tokens_used: int


@dataclass
class BatchResponse:
    """Response from batch operations."""
    batch_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    priority: str
    fail_fast: bool
    progress: BatchProgress
    cost: BatchCost
    job_ids: List[str]
    error_message: Optional[str]
    owner_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchResponse":
        """Create BatchResponse from API response dict."""
        progress = BatchProgress(**data.get("progress", {}))
        cost = BatchCost(**data.get("cost", {}))

        return cls(
            batch_id=data["batch_id"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00")) if data.get("completed_at") else None,
            priority=data.get("priority", "normal"),
            fail_fast=data.get("fail_fast", False),
            progress=progress,
            cost=cost,
            job_ids=data.get("job_ids", []),
            error_message=data.get("error_message"),
            owner_id=data.get("owner_id", ""),
        )


@dataclass
class UsageStatus:
    """Current usage and quota status."""
    user_id: str
    tier: str
    period: str
    days_remaining: int
    api_calls_used: int
    simulations_used: int
    cost_used_usd: float
    tokens_used: int
    api_calls_limit: int
    simulations_limit: int
    cost_limit_usd: float
    max_batch_size: int
    api_calls_remaining: int
    simulations_remaining: int
    cost_remaining_usd: float
    is_quota_exceeded: bool
    quota_exceeded_reason: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageStatus":
        """Create UsageStatus from API response dict."""
        return cls(
            user_id=data["user_id"],
            tier=data["tier"],
            period=data["period"],
            days_remaining=data["days_remaining"],
            api_calls_used=data["api_calls_used"],
            simulations_used=data["simulations_used"],
            cost_used_usd=data["cost_used_usd"],
            tokens_used=data["tokens_used"],
            api_calls_limit=data["api_calls_limit"],
            simulations_limit=data["simulations_limit"],
            cost_limit_usd=data["cost_limit_usd"],
            max_batch_size=data["max_batch_size"],
            api_calls_remaining=data["api_calls_remaining"],
            simulations_remaining=data["simulations_remaining"],
            cost_remaining_usd=data["cost_remaining_usd"],
            is_quota_exceeded=data["is_quota_exceeded"],
            quota_exceeded_reason=data.get("quota_exceeded_reason"),
        )


# ============================================================================
# Exceptions
# ============================================================================

class TimePointAPIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = None, response: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(TimePointAPIError):
    """Authentication failed."""
    pass


class QuotaExceededError(TimePointAPIError):
    """Usage quota exceeded."""
    pass


class BatchTooLargeError(TimePointAPIError):
    """Batch size exceeds tier limit."""
    pass


class BatchNotFoundError(TimePointAPIError):
    """Batch not found."""
    pass


class RateLimitError(TimePointAPIError):
    """Rate limit exceeded."""
    pass


# ============================================================================
# Client
# ============================================================================

class TimePointClient:
    """
    Client for the Timepoint Pro API.

    Provides methods for batch submission, status tracking, and usage monitoring.

    Args:
        api_key: API key for authentication. If not provided, reads from
                 TIMEPOINT_API_KEY environment variable.
        base_url: Base URL for the API. Defaults to http://localhost:8080.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.

    Example:
        client = TimePointClient(api_key="your-api-key")

        # Check if you have quota available
        usage = client.get_usage()
        if usage.simulations_remaining < 5:
            print("Low on quota!")

        # Submit a batch
        batch = client.submit_batch([
            {"template_id": "board_meeting", "entity_count": 4},
            {"template_id": "hospital_crisis", "entity_count": 3},
        ])

        # Wait for completion
        result = client.wait_for_batch(batch.batch_id, timeout=3600)
        print(f"Completed {result.progress.completed_jobs} jobs")
    """

    DEFAULT_BASE_URL = "http://localhost:8080"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("TIMEPOINT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Provide api_key argument or set TIMEPOINT_API_KEY env var."
            )

        self.base_url = (base_url or os.getenv("TIMEPOINT_API_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

        # Set up session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method,
                url,
                json=json,
                params=params,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise TimePointAPIError(
                f"Failed to connect to API at {self.base_url}. Is the server running?"
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimePointAPIError(
                f"Request timed out after {self.timeout}s"
            ) from e

        # Handle errors
        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid API key",
                status_code=401,
                response=response.json() if response.text else None,
            )
        elif response.status_code == 403:
            raise AuthenticationError(
                "Access denied",
                status_code=403,
                response=response.json() if response.text else None,
            )
        elif response.status_code == 404:
            raise BatchNotFoundError(
                "Resource not found",
                status_code=404,
                response=response.json() if response.text else None,
            )
        elif response.status_code == 429:
            data = response.json() if response.text else {}
            error_type = data.get("error", "")
            if "Quota" in error_type or "quota" in str(data):
                raise QuotaExceededError(
                    data.get("message", "Usage quota exceeded"),
                    status_code=429,
                    response=data,
                )
            else:
                raise RateLimitError(
                    data.get("message", "Rate limit exceeded"),
                    status_code=429,
                    response=data,
                )
        elif response.status_code == 400:
            data = response.json() if response.text else {}
            error_type = data.get("error", "")
            if "BatchTooLarge" in error_type:
                raise BatchTooLargeError(
                    data.get("message", "Batch size exceeds limit"),
                    status_code=400,
                    response=data,
                )
            raise TimePointAPIError(
                data.get("message", "Bad request"),
                status_code=400,
                response=data,
            )
        elif not response.ok:
            data = response.json() if response.text else {}
            raise TimePointAPIError(
                data.get("message", f"API error: {response.status_code}"),
                status_code=response.status_code,
                response=data,
            )

        return response.json()

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def submit_batch(
        self,
        simulations: List[Union[Dict, SimulationRequest]],
        budget_cap_usd: Optional[float] = None,
        priority: str = "normal",
        fail_fast: bool = False,
        parallel_jobs: int = 4,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchResponse:
        """
        Submit a batch of simulations.

        Args:
            simulations: List of simulation configurations. Each can be a dict with:
                - template_id: Template name (required)
                - entity_count: Number of entities (default: 3)
                - timepoint_count: Number of timepoints (default: 5)
                - custom_scenario: Optional custom scenario description
                - custom_entities: Optional list of entity configurations
            budget_cap_usd: Optional budget cap in USD
            priority: Priority level ("low", "normal", "high")
            fail_fast: Stop batch on first failure
            parallel_jobs: Number of parallel jobs (default: 4)
            metadata: Optional metadata dict

        Returns:
            BatchResponse with batch details

        Raises:
            QuotaExceededError: If simulation quota exceeded
            BatchTooLargeError: If batch size exceeds tier limit
            AuthenticationError: If API key is invalid
        """
        # Convert SimulationRequest objects to dicts
        sim_dicts = []
        for sim in simulations:
            if isinstance(sim, SimulationRequest):
                sim_dict = {
                    "template_id": sim.template_id,
                    "entity_count": sim.entity_count,
                    "timepoint_count": sim.timepoint_count,
                }
                if sim.custom_scenario:
                    sim_dict["custom_scenario"] = sim.custom_scenario
                if sim.custom_entities:
                    sim_dict["custom_entities"] = sim.custom_entities
                if sim.parameters:
                    sim_dict["parameters"] = sim.parameters
                sim_dicts.append(sim_dict)
            else:
                sim_dicts.append(sim)

        body = {
            "simulations": sim_dicts,
            "priority": priority,
            "fail_fast": fail_fast,
            "parallel_jobs": parallel_jobs,
        }
        if budget_cap_usd is not None:
            body["budget_cap_usd"] = budget_cap_usd
        if metadata:
            body["metadata"] = metadata

        data = self._request("POST", "/simulations/batch", json=body)
        return BatchResponse.from_dict(data)

    def get_batch_status(self, batch_id: str) -> BatchResponse:
        """
        Get the status of a batch.

        Args:
            batch_id: Batch ID

        Returns:
            BatchResponse with current status
        """
        data = self._request("GET", f"/simulations/batch/{batch_id}")
        return BatchResponse.from_dict(data)

    def cancel_batch(
        self,
        batch_id: str,
        reason: Optional[str] = None,
        cancel_running: bool = True,
    ) -> BatchResponse:
        """
        Cancel a batch.

        Args:
            batch_id: Batch ID
            reason: Optional cancellation reason
            cancel_running: Also cancel running jobs (default: True)

        Returns:
            BatchResponse with cancelled status
        """
        body = {"cancel_running": cancel_running}
        if reason:
            body["reason"] = reason

        data = self._request("POST", f"/simulations/batch/{batch_id}/cancel", json=body)
        return BatchResponse.from_dict(data)

    def list_batches(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List batches.

        Args:
            status: Filter by status (pending, running, completed, failed, cancelled)
            page: Page number (default: 1)
            page_size: Results per page (default: 20)

        Returns:
            Dict with 'batches', 'total', 'page', 'page_size'
        """
        params = {"page": page, "page_size": page_size}
        if status:
            params["status_filter"] = status

        data = self._request("GET", "/simulations/batch", params=params)

        # Convert batches to BatchResponse objects
        data["batches"] = [BatchResponse.from_dict(b) for b in data.get("batches", [])]
        return data

    def wait_for_batch(
        self,
        batch_id: str,
        timeout: int = 3600,
        poll_interval: int = 5,
        callback: Optional[callable] = None,
    ) -> BatchResponse:
        """
        Wait for a batch to complete.

        Args:
            batch_id: Batch ID
            timeout: Maximum wait time in seconds (default: 1 hour)
            poll_interval: Polling interval in seconds (default: 5)
            callback: Optional callback function called on each poll with BatchResponse

        Returns:
            BatchResponse with final status

        Raises:
            TimeoutError: If batch doesn't complete within timeout
        """
        start_time = time.time()
        terminal_states = {"completed", "failed", "cancelled"}

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Batch {batch_id} did not complete within {timeout}s"
                )

            batch = self.get_batch_status(batch_id)

            if callback:
                callback(batch)

            if batch.status in terminal_states:
                return batch

            time.sleep(poll_interval)

    # ========================================================================
    # Usage Operations
    # ========================================================================

    def get_usage(self) -> UsageStatus:
        """
        Get current usage and quota status.

        Returns:
            UsageStatus with current usage information
        """
        data = self._request("GET", "/simulations/batch/usage")
        return UsageStatus.from_dict(data)

    def get_usage_history(self, periods: int = 6) -> Dict[str, Any]:
        """
        Get usage history.

        Args:
            periods: Number of historical periods to include (default: 6)

        Returns:
            Dict with 'current' (UsageStatus) and 'history' (list of period summaries)
        """
        data = self._request("GET", "/simulations/batch/usage/history", params={"periods": periods})
        data["current"] = UsageStatus.from_dict(data["current"])
        return data

    def check_quota(self, simulation_count: int) -> bool:
        """
        Check if there's enough quota for a batch.

        Args:
            simulation_count: Number of simulations planned

        Returns:
            True if quota is available, False otherwise
        """
        usage = self.get_usage()

        if usage.is_quota_exceeded:
            return False

        if simulation_count > usage.simulations_remaining:
            return False

        if simulation_count > usage.max_batch_size:
            return False

        return True

    # ========================================================================
    # Health Check
    # ========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Check API health.

        Returns:
            Health status dict
        """
        return self._request("GET", "/health")

    def is_healthy(self) -> bool:
        """
        Check if API is healthy.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            health = self.health_check()
            return health.get("status") in ("healthy", "degraded")
        except Exception:
            return False


# ============================================================================
# Convenience Functions
# ============================================================================

def create_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> TimePointClient:
    """
    Create a TimePointClient with default configuration.

    Args:
        api_key: API key (defaults to TIMEPOINT_API_KEY env var)
        base_url: API base URL (defaults to TIMEPOINT_API_URL env var or localhost:8080)

    Returns:
        Configured TimePointClient
    """
    return TimePointClient(api_key=api_key, base_url=base_url)


def submit_batch_from_templates(
    templates: List[str],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    entity_count: int = 3,
    timepoint_count: int = 5,
    **kwargs,
) -> BatchResponse:
    """
    Convenience function to submit a batch from template names.

    Args:
        templates: List of template names
        api_key: Optional API key
        base_url: Optional API base URL
        entity_count: Default entity count for all templates
        timepoint_count: Default timepoint count for all templates
        **kwargs: Additional arguments passed to submit_batch

    Returns:
        BatchResponse
    """
    client = create_client(api_key=api_key, base_url=base_url)

    simulations = [
        {"template_id": t, "entity_count": entity_count, "timepoint_count": timepoint_count}
        for t in templates
    ]

    return client.submit_batch(simulations, **kwargs)
