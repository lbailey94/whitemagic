---
title: Example Long-Term Memory - Proven Heuristic
created: 2025-10-23T16:50:00
tags: ["heuristic", "debugging", "proven"]
---

## Heuristic: Debugging API Integration Issues

**Pattern Name**: API Troubleshooting Hierarchy

**When to Apply**: When debugging issues with external API integrations

**Proven Effective**: Validated across 10+ debugging sessions

## The Pattern

Check issues in this order:

1. **Authentication/Authorization** (60% of issues)
   - API keys valid and not expired?
   - Correct auth headers (Bearer, Basic, Custom)?
   - Permissions/scopes sufficient?

2. **Rate Limits** (20% of issues)
   - Check response headers for rate limit info
   - Implement exponential backoff
   - Consider caching to reduce calls

3. **Request Format** (15% of issues)
   - Content-Type header correct?
   - Body encoding matches expectation (JSON, form-data)?
   - Required fields present?

4. **Network/Infrastructure** (5% of issues)
   - Firewall rules allowing outbound?
   - DNS resolving correctly?
   - SSL/TLS certificate valid?

## Why This Works

Starting with auth catches the majority of issues quickly. Most API errors are permission-related, not code bugs.

## Code Example

```python
def debug_api_call(endpoint, headers, payload):
    """Systematic API debugging"""
    
    # 1. Verify auth
    print(f"Auth header: {headers.get('Authorization', 'MISSING')}")
    
    # 2. Check for rate limit hints
    if 'X-RateLimit-Remaining' in headers:
        print(f"Rate limit: {headers['X-RateLimit-Remaining']} remaining")
    
    # 3. Validate request format
    print(f"Content-Type: {headers.get('Content-Type')}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # 4. Make call with verbose error handling
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")
```

## Variations

- For GraphQL: Add schema validation to step 3
- For WebSocket: Add connection state checks
- For Streaming APIs: Add chunk handling verification

## Related Patterns

- "Exponential Backoff Implementation"
- "API Response Caching Strategy"
- "Secret Management Best Practices"

## Evolution History

- v1.0: Initial pattern (4 steps)
- v1.1: Added percentages from empirical data
- v1.2: Added code example and variations
