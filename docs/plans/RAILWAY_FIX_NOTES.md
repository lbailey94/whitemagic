# Railway Deployment Issue - 2.6.5

**Date**: November 16, 2025
**Status**: Fixed for 2.6.5

## Issue

Deployment failed with:

```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

## Root Cause

Railway sets `PORT` environment variable, but the CMD in Dockerfile wasn't interpolating it correctly. The `CMD` form wasn't expanding the variable.

## Fix Applied

Changed Dockerfile CMD from:

```dockerfile
CMD uvicorn whitemagic.api.app:app --host 2.6.5.0 --port ${PORT:-8000} --workers 2
```

To:

```dockerfile
CMD sh -c "uvicorn whitemagic.api.app:app --host 2.6.5.0 --port ${PORT:-8000} --workers 2"
```

Using `sh -c` ensures proper environment variable expansion.

## Verification for 2.6.5

- ✅ Dockerfile updated with explicit shell invocation
- ✅ Maintains default port 8000 fallback
- ✅ Works with Railway's dynamic PORT variable
- ✅ Non-root user preserved (whitemagic:1000)

## Learning

Railway requires explicit shell invocation for environment variable interpolation in Docker CMD. Using `sh -c` wrapper ensures variables are expanded at container runtime.
