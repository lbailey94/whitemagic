"""HTTP probe tool — send HTTP requests for API testing and vulnerability probing."""
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HTTPResponse:
    status_code: int
    headers: dict[str, str]
    body: str
    elapsed_ms: float
    url: str


class HTTPProbe:
    """HTTP client for security testing — supports various request types."""

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        self._history: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> HTTPResponse:
        return self._request("GET", url, params=params, headers=headers)

    def post(self, url: str, data: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> HTTPResponse:
        return self._request("POST", url, data=data, json_data=json_data, headers=headers)

    def put(self, url: str, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> HTTPResponse:
        return self._request("PUT", url, data=data, headers=headers)

    def delete(self, url: str, headers: dict[str, str] | None = None) -> HTTPResponse:
        return self._request("DELETE", url, headers=headers)

    def _request(self, method: str, url: str, **kwargs) -> HTTPResponse:
        import requests
        start = time.time()
        try:
            response = requests.request(
                method, url, timeout=self._timeout, **kwargs
            )
            elapsed = (time.time() - start) * 1000
            result = HTTPResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text[:5000],
                elapsed_ms=elapsed,
                url=url,
            )
            self._history.append({
                "method": method, "url": url, "status": response.status_code,
                "elapsed_ms": elapsed, "timestamp": time.time(),
            })
            return result
        except Exception as e:  # noqa: BLE001
            elapsed = (time.time() - start) * 1000
            return HTTPResponse(0, {}, str(e), elapsed, url)

    def probe_xss(self, url: str, param: str) -> dict[str, Any]:
        """Test for reflected XSS in a parameter."""
        payloads = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "\"><script>alert(document.cookie)</script>",
        ]
        results = []
        for payload in payloads:
            r = self.get(url, params={param: payload})
            reflected = payload in r.body
            unescaped = any(x in r.body for x in ["<script>", "onerror=", "onload="])
            results.append({
                "payload": payload,
                "reflected": reflected,
                "unescaped": unescaped,
                "vulnerable": reflected and unescaped,
                "status_code": r.status_code,
            })
        return {"url": url, "param": param, "results": results, "vulnerable": any(r["vulnerable"] for r in results)}

    def probe_sqli(self, url: str, param: str) -> dict[str, Any]:
        """Test for SQL injection in a parameter."""
        payloads = [
            "' OR '1'='1",
            "' UNION SELECT NULL--",
            "1' AND SLEEP(3)--",
            "'; DROP TABLE users--",
        ]
        results = []
        for payload in payloads:
            start = time.time()
            r = self.get(url, params={param: payload})
            elapsed = time.time() - start
            error_indicators = ["sql", "mysql", "postgres", "sqlite", "syntax", "error"]
            has_error = any(ind in r.body.lower() for ind in error_indicators)
            time_based = elapsed > 2.5  # SLEEP(3) would cause delay
            results.append({
                "payload": payload,
                "status_code": r.status_code,
                "error_detected": has_error,
                "time_based": time_based,
                "elapsed_s": elapsed,
                "vulnerable": has_error or time_based,
            })
        return {"url": url, "param": param, "results": results, "vulnerable": any(r["vulnerable"] for r in results)}

    def probe_idor(self, base_url: str, resource_path: str, max_id: int = 20) -> dict[str, Any]:
        """Test for IDOR by iterating resource IDs."""
        accessible = []
        for rid in range(1, max_id + 1):
            r = self.get(f"{base_url}/{resource_path}/{rid}")
            if r.status_code == 200:
                accessible.append({"id": rid, "body_length": len(r.body), "body_snippet": r.body[:200]})
        return {
            "base_url": base_url,
            "resource_path": resource_path,
            "accessible_count": len(accessible),
            "accessible": accessible,
            "vulnerable": len(accessible) > 5,
        }

    def probe_ssrf(self, url: str, param: str) -> dict[str, Any]:
        """Test for SSRF by injecting internal URLs."""
        payloads = [
            "http://localhost:80",
            "http://127.0.0.1:80",
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://[::1]:80",
            "file:///etc/passwd",
        ]
        results = []
        for payload in payloads:
            r = self.get(url, params={param: payload})
            internal_indicators = ["root:", "ami-id", "instance-id", "localhost", "127.0.0.1"]
            has_internal = any(ind in r.body.lower() for ind in internal_indicators)
            results.append({
                "payload": payload,
                "status_code": r.status_code,
                "internal_data_exposed": has_internal,
                "body_length": len(r.body),
                "vulnerable": has_internal,
            })
        return {"url": url, "param": param, "results": results, "vulnerable": any(r["vulnerable"] for r in results)}

    def api_state_machine(self, base_url: str, sequences: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """Run API call sequences and detect state inconsistencies.

        Each sequence is a list of steps: [{"method": "POST", "path": "/api/login", "json": {...}}, ...]
        """
        results = []
        for seq_idx, sequence in enumerate(sequences):
            state_changes = []
            for step in sequence:
                method = step.get("method", "GET")
                path = step.get("path", "/")
                url = f"{base_url}{path}"
                if method == "GET":
                    r = self.get(url, headers=step.get("headers"))
                elif method == "POST":
                    r = self.post(url, json_data=step.get("json"), headers=step.get("headers"))
                elif method == "PUT":
                    r = self.put(url, data=step.get("data"), headers=step.get("headers"))
                elif method == "DELETE":
                    r = self.delete(url, headers=step.get("headers"))
                else:
                    continue
                state_changes.append({
                    "step": method + " " + path,
                    "status": r.status_code,
                    "body_length": len(r.body),
                })
            results.append({
                "sequence": seq_idx,
                "steps": state_changes,
                "completed": True,
            })
        return {"base_url": base_url, "sequences_run": len(results), "results": results}

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()


_probe: HTTPProbe | None = None


def get_http_probe() -> HTTPProbe:
    global _probe
    if _probe is None:
        _probe = HTTPProbe()
    return _probe
