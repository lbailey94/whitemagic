# Security Policy

## 🔒 Security at WhiteMagic

We take the security of WhiteMagic seriously. This document outlines our security policies, vulnerability disclosure process, and security best practices.

---

## 📋 Supported Versions

We actively maintain security updates for the following versions:

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 2.1.x   | ✅ Yes | Current stable release |
| 2.0.x   | ⚠️ Limited | Security fixes only until 2025-12-31 |
| < 2.0   | ❌ No | Please upgrade to 2.1.x |

**Recommendation**: Always use the latest 2.1.x release for the best security and features.

---

## 🚨 Reporting a Vulnerability

### **Where to Report**

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security issues to:
- **Email**: security@whitemagic.dev (or lbailey94@github if dedicated email not available)
- **GitHub Security Advisory**: [Create a private security advisory](https://github.com/lbailey94/whitemagic/security/advisories/new)

### **What to Include**

Please include the following information:
1. **Description** - Clear description of the vulnerability
2. **Impact** - What could an attacker accomplish?
3. **Steps to Reproduce** - Detailed steps to reproduce the issue
4. **Version** - Affected version(s) of WhiteMagic
5. **Environment** - OS, Python version, deployment type (API/CLI/MCP)
6. **Proof of Concept** - Code snippet or video demonstrating the issue (if applicable)

### **Response Timeline**

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Within 30 days for high/critical issues
- **Public Disclosure**: After patch is released and users have had time to upgrade

### **Rewards**

While we don't have a formal bug bounty program, we will:
- Publicly acknowledge reporters (with permission)
- Add your name to our security hall of fame
- Provide early access to new features

---

## 🛡️ Security Features

### **Authentication & Authorization**
- ✅ API key-based authentication
- ✅ SHA-256 key hashing (never store plaintext)
- ✅ Key rotation support
- ✅ Per-key permissions and metadata
- ✅ Rate limiting per user/key

### **API Security**
- ✅ Input validation on all endpoints
- ✅ SQL injection protection (SQLAlchemy parameterized queries)
- ✅ XSS protection headers
- ✅ CORS configuration
- ✅ Request size limits
- ✅ Rate limiting middleware

### **Infrastructure Security**
- ✅ Docker container hardening (non-root user, dropped capabilities)
- ✅ Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- ✅ Environment variable protection
- ✅ Secure defaults
- ✅ TLS/HTTPS support

### **Dependency Management**
- ✅ Automated dependency updates (Dependabot)
- ✅ Vulnerability scanning (GitHub Advanced Security)
- ✅ CodeQL static analysis
- ✅ License compliance checks
- ✅ Weekly security audits

### **Monitoring & Logging**
- ✅ Structured JSON logging
- ✅ Correlation ID tracking
- ✅ Usage analytics
- ✅ Audit trail for sensitive operations
- ✅ No sensitive data in logs

---

## 🔐 Security Best Practices

### **For Users**

#### **API Key Management**
```bash
# ❌ DON'T: Commit API keys to git
echo "WM_API_KEY=wm_prod_abc123..." >> config.py

# ✅ DO: Use environment variables
export WM_API_KEY=wm_prod_abc123...

# ✅ DO: Use .env files (add to .gitignore)
echo "WM_API_KEY=wm_prod_abc123..." >> .env
```

#### **Docker Deployment**
```bash
# ✅ DO: Use security hardening options
docker run \
  --user 1000:1000 \
  --cap-drop=ALL \
  --read-only \
  --security-opt=no-new-privileges:true \
  -v whitemagic-data:/data \
  --tmpfs /tmp \
  whitemagic:2.1.1
```

#### **Database Security**
```bash
# ❌ DON'T: Use weak passwords
DATABASE_URL=postgresql://user:password@localhost/db

# ✅ DO: Use strong, unique passwords
DATABASE_URL=postgresql://user:$(openssl rand -base64 32)@localhost/db

# ✅ DO: Use connection pooling limits
DATABASE_URL=postgresql://user:pass@localhost/db?pool_size=20&max_overflow=10
```

#### **Rate Limiting**
- Configure rate limits based on your tier:
  - **Free**: 100 requests/day
  - **Starter**: 1,000 requests/day
  - **Pro**: 10,000 requests/day
  - **Enterprise**: Custom limits

### **For Contributors**

#### **Code Review Checklist**
- [ ] No hardcoded credentials or API keys
- [ ] Input validation on all user inputs
- [ ] SQL queries use parameterized statements
- [ ] No sensitive data in logs
- [ ] Error messages don't leak implementation details
- [ ] Dependencies are up to date
- [ ] Tests cover security edge cases

#### **Commit Signing**
```bash
# Enable GPG signing for commits
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY_ID
```

---

## 🔍 Security Scanning

### **Automated Scans**

We run the following automated security scans:

1. **CodeQL** - Static analysis on every push
2. **Dependabot** - Weekly dependency updates
3. **Safety** - Python dependency vulnerability scan
4. **Bandit** - Security linting for Python code
5. **Docker Scanning** - Container image vulnerability scan
6. **License Compliance** - Check for incompatible licenses

### **Manual Testing**

Before each release, we perform:
- Penetration testing on API endpoints
- Authentication/authorization bypass attempts
- SQL injection testing
- XSS testing
- CSRF testing
- Rate limit bypass attempts

---

## 📝 Known Security Considerations

### **Current Limitations**

1. **API Keys in Transit**: API keys are sent in headers. Always use HTTPS in production.
2. **SQLite for Development**: SQLite doesn't support advanced security features. Use PostgreSQL in production.
3. **No Built-in 2FA**: Two-factor authentication is not currently supported. Coming in v2.2.
4. **Rate Limiting**: Rate limits are per-key, not per-IP. Can be bypassed with multiple keys.

### **Mitigation Strategies**

1. **Use HTTPS**: Always deploy with TLS/HTTPS enabled
2. **PostgreSQL in Production**: Use PostgreSQL for row-level security and better audit
3. **External 2FA**: Use an API gateway or reverse proxy for 2FA
4. **IP-based Rate Limiting**: Use nginx/Cloudflare for IP-based rate limiting

---

## 🏆 Security Hall of Fame

We'd like to thank the following researchers for responsibly disclosing security issues:

*(No reports yet - be the first!)*

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [API Security Best Practices](https://github.com/OWASP/API-Security)

---

## 📧 Contact

- **Security Issues**: security@whitemagic.dev
- **General Questions**: [GitHub Discussions](https://github.com/lbailey94/whitemagic/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/lbailey94/whitemagic/issues)

---

**Last Updated**: November 10, 2025  
**Version**: 2.1.1
