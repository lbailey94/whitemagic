# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 25.x    | :white_check_mark: |
| 24.x    | :white_check_mark: |
| < 24.0  | :x:                |

## Reporting a Vulnerability

We take the security of WhiteMagic seriously. If you have discovered a security vulnerability, please report it privately.

**Do NOT file a public issue.**

Instead, please report vulnerabilities by:

1. Opening a GitHub Security Advisory (preferred)
2. Emailing security@whitemagic.dev

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a detailed response within 7 days.

## Security Features

WhiteMagic includes built-in safety mechanisms:

- **Governor**: Pre-execution validation for forbidden actions
- **Input Sanitizer**: Validates and sanitizes all tool inputs
- **Rate Limiter**: Prevents resource exhaustion
- **Tool Permissions**: Fine-grained access control for each PRAT Gana
- **Constitutional Checks**: Ethical governance constraints

See `docs/CONTRIBUTING.md` for details on the safety architecture.
