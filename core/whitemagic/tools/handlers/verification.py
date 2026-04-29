"""Verification and attestation handlers."""
from typing import Any

_verifications: dict[str, dict[str, Any]] = {}


def handle_verification_request(**kwargs: Any) -> dict[str, Any]:
    target = kwargs.get("target", "")
    if not target:
        return {"status": "error", "error_code": "invalid_params", "message": "target is required"}
    req_id = kwargs.get("request_id", f"ver_{len(_verifications)}")
    _verifications[req_id] = {"target": target, "status": "pending", "attestations": []}
    return {"status": "pending", "request_id": req_id, "target": target}


def handle_verification_attest(**kwargs: Any) -> dict[str, Any]:
    req_id = kwargs.get("request_id", "")
    attestation = kwargs.get("attestation", "")
    if not req_id or not attestation:
        return {"status": "error", "error_code": "invalid_params", "message": "request_id and attestation are required"}
    if req_id not in _verifications:
        return {"status": "error", "error_code": "not_found", "message": f"Request {req_id} not found"}
    _verifications[req_id]["attestations"].append(attestation)
    count = len(_verifications[req_id]["attestations"])
    _verifications[req_id]["status"] = "attested" if count >= 2 else "pending"
    return {"status": "success", "request_id": req_id, "attestation_count": count}


def handle_verification_status(**kwargs: Any) -> dict[str, Any]:
    req_id = kwargs.get("request_id", "")
    if req_id:
        if req_id not in _verifications:
            return {"status": "error", "error_code": "not_found", "message": f"Request {req_id} not found"}
        return {"status": "success", "verification": _verifications[req_id]}
    return {"status": "success", "verifications": list(_verifications.keys()), "count": len(_verifications)}
