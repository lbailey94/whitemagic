import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow running from repo root without requiring installation.
REPO_ROOT = Path(os.environ.get("WM_REPO_ROOT", Path(__file__).resolve().parent.parent)).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from whitemagic.core.ganas.base import GanaCall
    from whitemagic.core.ganas.southern_quadrant import ChariotGana, GhostGana, ExtendedNetGana
    from whitemagic.core.ganas.western_quadrant import NetGana
    from whitemagic.core.ganas.eastern_quadrant import WinnowingBasketGana, RootGana
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

PROJECT_ROOT = REPO_ROOT
OUTPUT_FILE = "project_audit.md"

class ProjectAuditor:
    def __init__(self):
        self.chariot = ChariotGana()
        self.net = NetGana()
        self.extended_net = ExtendedNetGana()
        self.ghost = GhostGana()
        self.basket = WinnowingBasketGana()
        self.root = RootGana()
        self.findings = {}

    async def scan_structure(self):
        print("1. [Chariot] Scanning project structure...")
        # Simulating Chariot scan - in real scenario it would traverse
        # Here we manually walk to feed data to Ganas
        
        tree_stats = {"files": 0, "dirs": 0, "extensions": {}}
        file_list = []
        
        for root, dirs, files in os.walk(PROJECT_ROOT):
            if ".git" in root or "__pycache__" in root or "node_modules" in root:
                continue
            
            tree_stats["dirs"] += len(dirs)
            tree_stats["files"] += len(files)
            
            for f in files:
                ext = os.path.splitext(f)[1]
                tree_stats["extensions"][ext] = tree_stats["extensions"].get(ext, 0) + 1
                file_list.append(os.path.join(root, f))
                
        self.findings["structure"] = tree_stats
        self.findings["file_list"] = file_list
        print(f"   -> Found {tree_stats['files']} files in {tree_stats['dirs']} directories.")

    async def analyze_patterns(self):
        print("2. [Net] Analyzing code patterns...")
        
        todos = 0
        fixmes = 0
        classes = 0
        defs = 0
        
        # Limit scan to python/md files for speed
        scan_files = [f for f in self.findings["file_list"] if f.endswith(('.py', '.md'))]
        
        for fpath in scan_files:
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    todos += content.count("TODO")
                    fixmes += content.count("FIXME")
                    classes += content.count("class ")
                    defs += content.count("def ")
            except Exception:
                pass
                
        # Invoke NetGana to "store" this pattern (simulated)
        call = GanaCall(
            task="detect_patterns", 
            state_vector={
                "content": "project_scan", 
                "stats": {"todos": todos, "fixmes": fixmes}
            }
        )
        await self.net.invoke(call)
        
        self.findings["patterns"] = {
            "TODOs": todos,
            "FIXMEs": fixmes,
            "Classes defined": classes,
            "Functions defined": defs
        }
        print(f"   -> Detected {todos} TODOs, {fixmes} FIXMEs.")

    async def check_health(self):
        print("3. [Root] Checking system health...")
        # Invoke RootGana
        call = GanaCall(task="check_system_health", state_vector={"deep_scan": True})
        result = await self.root.invoke(call)
        self.findings["health"] = result.output

    async def generate_report(self):
        print("4. [Winnowing Basket] Generating report...")
        
        report = f"""# Project Audit: WhiteMagic Global Analysis
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Root**: `{PROJECT_ROOT}`

## 1. Structural Overview (Chariot)
- **Total Files**: {self.findings['structure']['files']}
- **Directories**: {self.findings['structure']['dirs']}
- **File Types**:
"""
        # Sort extensions by count
        sorted_exts = sorted(self.findings['structure']['extensions'].items(), key=lambda x: x[1], reverse=True)
        for ext, count in sorted_exts[:10]:
            report += f"  - `{ext or 'no_ext'}`: {count}\n"

        report += f"""
## 2. Code Patterns (Net)
- **Classes**: {self.findings['patterns']['Classes defined']}
- **Functions**: {self.findings['patterns']['Functions defined']}
- **Technical Debt Indicators**:
  - `TODO`: {self.findings['patterns']['TODOs']}
  - `FIXME`: {self.findings['patterns']['FIXMEs']}

## 3. System Health (Root)
- **Integrity**: {self.findings.get('health', {}).get('integrity', 'Unknown')}
- **Health Check**: {self.findings.get('health', {}).get('health_check', 'Unknown')}
- **Metrics**:
  - Harmony Score: {self.findings.get('health', {}).get('metrics', {}).get('harmony_score', 'N/A')}
  - Guna State: {self.findings.get('health', {}).get('metrics', {}).get('guna', 'N/A')}

## 4. Recommendations
"""
        if self.findings['patterns']['TODOs'] > 50:
            report += "- [High] Technical debt accumulation (high TODO count). Schedule cleanup sprint.\n"
        if self.findings['structure']['extensions'].get('.py', 0) > 1000:
            report += "- [Medium] Large Python codebase. Consider modularizing into micro-services if not already.\n"
        
        report += "\n*Generated by Gana System Logic*"
        
        with open(OUTPUT_FILE, "w") as f:
            f.write(report)
            
        print(f"   -> Report written to {OUTPUT_FILE}")

    async def run(self):
        await self.scan_structure()
        await self.analyze_patterns()
        await self.check_health()
        await self.generate_report()

if __name__ == "__main__":
    auditor = ProjectAuditor()
    asyncio.run(auditor.run())
