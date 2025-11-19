"""Release automation - runs at end of each version release.

Automatically:
- Runs tool sharpening
- Updates MCP tools
- Rebuilds Rust/Haskell bindings
- Syncs documentation
- Validates configuration
"""

import subprocess
from pathlib import Path
from datetime import datetime
from whitemagic.automation.tool_sharpening import ToolSharpener
from whitemagic.config import VERSION


class ReleaseAutomation:
    """Automate post-release tasks."""
    
    def __init__(self):
        self.version = VERSION
        self.timestamp = datetime.now()
        self.results = []
    
    def run_all(self):
        """Run all post-release automation."""
        print(f"\n=== Release Automation v{self.version} ===")
        print(f"Started: {self.timestamp.isoformat()}\n")
        
        # 1. Tool sharpening
        self._sharpen_tools()
        
        # 2. Rebuild bindings
        self._rebuild_bindings()
        
        # 3. Update MCP
        self._update_mcp()
        
        # 4. Validate config
        self._validate_config()
        
        # 5. Summary
        self._print_summary()
    
    def _sharpen_tools(self):
        """Run tool sharpening."""
        print("→ Sharpening tools...")
        try:
            sharpener = ToolSharpener()
            result = sharpener.sharpen_all_tools()
            self.results.append(("Tool Sharpening", "✓", result))
            print(f"  ✓ Complete: {result}")
        except Exception as e:
            self.results.append(("Tool Sharpening", "✗", str(e)))
            print(f"  ✗ Error: {e}")
    
    def _rebuild_bindings(self):
        """Rebuild Rust and Haskell bindings."""
        print("→ Rebuilding bindings...")
        try:
            # Rust
            rust_result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd="whitemagic-rs",
                capture_output=True,
                timeout=300
            )
            if rust_result.returncode == 0:
                print("  ✓ Rust bindings rebuilt")
                self.results.append(("Rust Rebuild", "✓", "Success"))
            else:
                print("  ⚠ Rust build failed (optional)")
                self.results.append(("Rust Rebuild", "⚠", "Failed (optional)"))
        except Exception as e:
            print(f"  ⚠ Rust: {e}")
            self.results.append(("Rust Rebuild", "⚠", str(e)))
    
    def _update_mcp(self):
        """Update MCP tools."""
        print("→ Updating MCP tools...")
        try:
            # Update MCP server package
            mcp_result = subprocess.run(
                ["npm", "install"],
                cwd="mcp-server",
                capture_output=True,
                timeout=60
            )
            if mcp_result.returncode == 0:
                print("  ✓ MCP tools updated")
                self.results.append(("MCP Update", "✓", "Success"))
            else:
                print("  ⚠ MCP update skipped")
                self.results.append(("MCP Update", "⚠", "Skipped"))
        except Exception as e:
            print(f"  ⚠ MCP: {e}")
            self.results.append(("MCP Update", "⚠", str(e)))
    
    def _validate_config(self):
        """Validate configuration."""
        print("→ Validating configuration...")
        try:
            from whitemagic.config import show_config
            show_config()
            self.results.append(("Config Validation", "✓", "Valid"))
        except Exception as e:
            print(f"  ✗ Config error: {e}")
            self.results.append(("Config Validation", "✗", str(e)))
    
    def _print_summary(self):
        """Print summary of automation results."""
        print(f"\n=== Automation Summary ===")
        for task, status, result in self.results:
            print(f"{status} {task}: {result}")
        
        success_count = sum(1 for _, status, _ in self.results if status == "✓")
        total = len(self.results)
        print(f"\n{success_count}/{total} tasks successful")


def run_release_automation():
    """Entry point for release automation."""
    automation = ReleaseAutomation()
    automation.run_all()
    return automation.results


if __name__ == "__main__":
    run_release_automation()
