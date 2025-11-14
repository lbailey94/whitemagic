#\!/bin/bash
# Fix critical issues from independent review

# 1. Fix allowlist - update signature
sed -i 's/def is_allowed(self, cmd: str)/def is_allowed(self, cmd: str, args: Optional[List[str]] = None)/' whitemagic/terminal/allowlist.py

# 2. Fix numpy dependency
sed -i 's/"api" = \[/"api" = \["numpy",/' pyproject.toml

# 3. Fix CI escape hatch
sed -i 's/npm test || echo "No MCP tests yet"/npm test/' .github/workflows/ci.yml

# 4. Fix compose to build locally
sed -i 's|image: lbailey94/whitemagic:2.1.0|build: .|' compose.yaml

echo "Critical fixes applied"
