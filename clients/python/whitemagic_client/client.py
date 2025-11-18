"""WhiteMagic Python SDK client."""

import time

import httpx

from .exceptions import WhiteMagicError
from .types import (
    CreateMemoryRequest,
    HealthResponse,
    ListMemoriesParams,
    Memory,
    SearchMemoriesParams,
    UpdateMemoryRequest,
    UsageStats,
    User,
)


class WhiteMagicClient:
    """WhiteMagic API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.whitemagic.dev",
        timeout: float = 30.0,
        retries: int = 3,
    ):
        """Initialize WhiteMagic client.

        Args:
            api_key: Your WhiteMagic API key
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds
            retries: Number of retry attempts for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._client = httpx.Client(
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | list | None:
        """Make an HTTP request with retry logic."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                )

                if not response.is_success:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass

                    raise WhiteMagicError(
                        error_data.get("message")
                        or f"HTTP {response.status_code}: {response.reason_phrase}",
                        status=response.status_code,
                        code=error_data.get("code"),
                        details=error_data.get("details"),
                    )

                # Handle 204 No Content
                if response.status_code == 204:
                    return None

                return response.json()

            except WhiteMagicError as e:
                # Don't retry client errors (4xx)
                if e.status and 400 <= e.status < 500:
                    raise
                last_error = e

            except Exception as e:
                last_error = e

            # Don't retry on last attempt
            if attempt == self.retries:
                break

            # Exponential backoff
            time.sleep(2**attempt)

        raise last_error or WhiteMagicError("Request failed after retries")

    # Memory operations
    def create_memory(self, request: CreateMemoryRequest | dict) -> Memory:
        """Create a new memory."""
        if isinstance(request, CreateMemoryRequest):
            data = request.model_dump(exclude_none=True)
        else:
            data = request
        result = self._request("POST", "/api/v1/memories", json=data)
        return Memory(**result)

    def list_memories(self, params: ListMemoriesParams | dict | None = None) -> list[Memory]:
        """List memories with optional filtering."""
        query_params = None
        if params:
            if isinstance(params, ListMemoriesParams):
                query_params = params.model_dump(exclude_none=True)
            else:
                query_params = params

        result = self._request("GET", "/api/v1/memories", params=query_params)
        return [Memory(**m) for m in result]

    def get_memory(self, memory_id: str) -> Memory:
        """Get a specific memory by ID."""
        result = self._request("GET", f"/api/v1/memories/{memory_id}")
        return Memory(**result)

    def update_memory(
        self,
        memory_id: str,
        request: UpdateMemoryRequest | dict,
    ) -> Memory:
        """Update an existing memory."""
        if isinstance(request, UpdateMemoryRequest):
            data = request.model_dump(exclude_none=True)
        else:
            data = request
        result = self._request("PUT", f"/api/v1/memories/{memory_id}", json=data)
        return Memory(**result)

    def delete_memory(self, memory_id: str) -> None:
        """Delete (archive) a memory."""
        self._request("DELETE", f"/api/v1/memories/{memory_id}")

    def restore_memory(self, memory_id: str) -> Memory:
        """Restore an archived memory."""
        result = self._request("POST", f"/api/v1/memories/{memory_id}/restore")
        return Memory(**result)

    def search_memories(self, params: SearchMemoriesParams | dict) -> list[Memory]:
        """Search memories using semantic search."""
        query_params = None
        if isinstance(params, SearchMemoriesParams):
            query_params = params.model_dump(exclude_none=True)
        else:
            query_params = params

        result = self._request("GET", "/api/v1/search", params=query_params)
        return [Memory(**m) for m in result]

    def add_relationship(
        self, memory_id: str, target_id: str, relationship_type: str, description: str | None = None
    ) -> dict:
        """Add a relationship between two memories."""
        data = {"target_filename": target_id, "type": relationship_type, "description": description}
        result = self._request("POST", f"/api/v1/memories/{memory_id}/relationships", json=data)
        return result

    def get_relationships(self, memory_id: str) -> list[dict]:
        """Get all relationships for a memory."""
        result = self._request("GET", f"/api/v1/memories/{memory_id}/relationships")
        return result

    # User operations
    def get_current_user(self) -> User:
        """Get current user information."""
        result = self._request("GET", "/api/v1/users/me")
        return User(**result)

    def get_usage_stats(self) -> UsageStats:
        """Get usage statistics for current user."""
        result = self._request("GET", "/api/v1/users/me/usage")
        return UsageStats(**result)

    # System operations
    def health_check(self) -> HealthResponse:
        """Check API health status."""
        result = self._request("GET", "/health")
        return HealthResponse(**result)
