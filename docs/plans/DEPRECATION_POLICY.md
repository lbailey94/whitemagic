# WhiteMagic API Deprecation Policy

**Version**: 2.6.5
**Last Updated**: November 10, 2025

---

## 📋 Overview

WhiteMagic follows a structured deprecation policy to ensure stability for integrators while allowing the API to evolve. This document outlines how we handle breaking changes, deprecations, and version transitions.

---

## 🎯 Versioning Strategy

### **Version Format**

We use Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to API contract
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, backward-compatible

### **Current Version**

- **API Version**: `v1`
- **Release**: `2.6.5`

---

## ⏱️ Deprecation Timeline

### **Standard Deprecation Period: 90 Days**

When an endpoint, parameter, or feature is deprecated:

1. **Day 0**: Deprecation announced
   - Added to `/openapi.json` with `deprecated: true`
   - `Deprecation` header sent with affected endpoints
   - Documented in changelog and API docs

2. **Days 1-90**: Grace period
   - Feature continues to work normally
   - Warnings in logs (structured JSON)
   - Migration guide published

3. **Day 91+**: Feature removed
   - Returns `410 Gone` for deprecated endpoints
   - Missing parameters ignored or return errors

---

## 📢 Deprecation Headers

When you use a deprecated feature, the API returns:

```http
Deprecation: Sun, 11 Nov 2025 00:00:00 GMT
Sunset: Wed, 11 Feb 2026 00:00:00 GMT
Link: <https://docs.whitemagic.dev/migrations/v2>; rel="deprecation"
```

- **Deprecation**: When the feature was marked deprecated
- **Sunset**: When the feature will be removed
- **Link**: Migration guide URL

---

## 🔄 Migration Support

### **OpenAPI Schema Freeze**

- `/openapi.json` endpoint provides frozen v1 API schema
- Use for code generation and contract testing
- Schema version tracked via `X-WhiteMagic-Revision` header

### **Version Pinning**

- Pin to specific version: `X-API-Version: v1`
- Future: `/api/v2/...` for major version changes

---

## 📝 Current Deprecations

**None**: All current endpoints are fully supported.

---

## 🚀 Breaking Change Policy

### **When We Introduce Breaking Changes**

1. Release new major version (e.g., 2.6.5)
2. Support previous version for minimum 12 months
3. Provide automated migration tools when possible

### **What Counts as Breaking**

- Removing endpoints
- Changing required parameters
- Modifying response structure for existing fields
- Changing authentication requirements

### **What's NOT Breaking**

- Adding new optional parameters
- Adding new response fields
- Adding new endpoints
- Performance improvements
- Bug fixes

---

## 📞 Support

Questions about deprecations? Contact:

- **GitHub Issues**: <https://github.com/lbailey94/whitemagic/issues>
- **Email**: <support@whitemagic.dev>

---

## 📅 Version History

| Version | Release Date | Support Until |
|---------|-------------|---------------|
| v1      | 2.6.5       | Current       |
| Nov 10, 2025 | Active        |
| 2.6.5   | Nov 9, 2025  | Active        |
| 2.6.5   | Nov 1, 2025  | Nov 1, 2026   |
