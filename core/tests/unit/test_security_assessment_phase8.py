"""Tests for Security Capabilities Assessment Phase 8: Security Dashboard.

Covers:
  - Security status API endpoint fallback data
  - SecurityDashboard component structure
  - Sitemap includes /security
  - API route exists and returns JSON
"""

import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase8_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


class TestSecurityDashboardPage:
    """Test that the security dashboard page exists."""

    def test_page_file_exists(self):
        p = Path(__file__).resolve().parents[3] / "app" / "security" / "page.tsx"
        assert p.exists(), f"Security page not found at {p}"

    def test_page_exports_default(self):
        p = Path(__file__).resolve().parents[3] / "app" / "security" / "page.tsx"
        content = p.read_text()
        assert "export default" in content
        assert "SecurityDashboard" in content

    def test_page_has_metadata(self):
        p = Path(__file__).resolve().parents[3] / "app" / "security" / "page.tsx"
        content = p.read_text()
        assert "metadata" in content
        assert "Security" in content


class TestSecurityAPIRoute:
    """Test that the security status API route exists."""

    def test_route_file_exists(self):
        p = Path(__file__).resolve().parents[3] / "app" / "api" / "security" / "status" / "route.ts"
        assert p.exists(), f"Security API route not found at {p}"

    def test_route_exports_get(self):
        p = Path(__file__).resolve().parents[3] / "app" / "api" / "security" / "status" / "route.ts"
        content = p.read_text()
        assert "export async function GET" in content
        assert "NextResponse" in content

    def test_route_has_fallback_data(self):
        p = Path(__file__).resolve().parents[3] / "app" / "api" / "security" / "status" / "route.ts"
        content = p.read_text()
        assert "event_bus" in content
        assert "hermit_crab" in content
        assert "transaction_firewall" in content
        assert "engagement_tokens" in content
        assert "mcp_integrity" in content
        assert "vuln_kb" in content
        assert "audit_signer" in content
        assert "zodiac_ledger" in content


class TestSecurityDashboardComponent:
    """Test that the SecurityDashboard component exists."""

    def test_component_file_exists(self):
        p = Path(__file__).resolve().parents[3] / "components" / "SecurityDashboard.tsx"
        assert p.exists(), f"SecurityDashboard component not found at {p}"

    def test_component_is_client_component(self):
        p = Path(__file__).resolve().parents[3] / "components" / "SecurityDashboard.tsx"
        content = p.read_text()
        assert '"use client"' in content

    def test_component_has_stat_cards(self):
        p = Path(__file__).resolve().parents[3] / "components" / "SecurityDashboard.tsx"
        content = p.read_text()
        assert "StatCard" in content
        assert "HermitCrab" in content

    def test_component_has_event_feed(self):
        p = Path(__file__).resolve().parents[3] / "components" / "SecurityDashboard.tsx"
        content = p.read_text()
        assert "Recent Security Events" in content or "recent_events" in content

    def test_component_has_ledger_section(self):
        p = Path(__file__).resolve().parents[3] / "components" / "SecurityDashboard.tsx"
        content = p.read_text()
        assert "Zodiac Ledger" in content or "zodiac_ledger" in content


class TestSitemapIncludesSecurity:
    """Test that the sitemap includes /security."""

    def test_security_in_sitemap(self):
        p = Path(__file__).resolve().parents[3] / "app" / "sitemap.ts"
        content = p.read_text()
        assert "/security" in content
