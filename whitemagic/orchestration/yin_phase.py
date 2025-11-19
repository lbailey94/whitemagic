"""Yin Phase - Deep Receptive Analysis

坤 (Kūn) - The Receptive Earth
- Observe everything
- Judge nothing
- Learn deeply
- Consolidate memory
- Self-correct
"""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

class YinPhase:
    """Automated deep reflection and analysis"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.analysis_dir = self.base_dir / "memory" / "yin_analyses"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
    
    def run_full_cycle(self) -> Dict[str, Any]:
        """Execute complete Yin cycle"""
        print("🌑 Yin Phase: Deep receptive analysis beginning...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'yin',
            'analyses': {}
        }
        
        # 1. Pattern analysis
        print("  📊 Analyzing patterns...")
        results['analyses']['patterns'] = self._analyze_patterns()
        
        # 2. Gap detection
        print("  🔍 Detecting gaps...")
        results['analyses']['gaps'] = self._detect_gaps()
        
        # 3. Error analysis
        print("  ❌ Analyzing errors...")
        results['analyses']['errors'] = self._analyze_errors()
        
        # 4. Documentation audit
        print("  📚 Auditing documentation...")
        results['analyses']['docs'] = self._audit_documentation()
        
        # 5. Memory consolidation
        print("  💾 Consolidating memories...")
        results['analyses']['consolidation'] = self._consolidate_memories()
        
        # 6. Learning integration
        print("  🧠 Integrating learnings...")
        results['analyses']['learning'] = self._integrate_learning()
        
        # Save analysis
        self._save_analysis(results)
        
        print("🌕 Yin Phase complete: All patterns observed")
        return results
    
    def _analyze_patterns(self) -> Dict[str, Any]:
        """Analyze all patterns in system"""
        # Scan for pattern files
        pattern_dirs = [
            self.base_dir / "whitemagic" / "autoimmune",
            self.base_dir / "whitemagic" / "solutions",
            self.base_dir / "whitemagic" / "wu_xing"
        ]
        
        total_patterns = 0
        by_type = {}
        
        for dir in pattern_dirs:
            if dir.exists():
                py_files = list(dir.glob("*.py"))
                total_patterns += len(py_files)
                by_type[dir.name] = len(py_files)
        
        return {
            'total': total_patterns,
            'by_type': by_type,
            'status': 'analyzed'
        }
    
    def _detect_gaps(self) -> Dict[str, Any]:
        """Detect gaps in implementation"""
        gaps = []
        
        # Check for TODOs in code
        todo_files = []
        for py_file in (self.base_dir / "whitemagic").rglob("*.py"):
            content = py_file.read_text()
            if 'TODO' in content or 'FIXME' in content:
                todo_files.append(str(py_file.relative_to(self.base_dir)))
        
        if todo_files:
            gaps.append({
                'type': 'unimplemented_features',
                'count': len(todo_files),
                'files': todo_files[:10]  # First 10
            })
        
        # Check for missing integrations
        rust_integrated = (self.base_dir / "whitemagic" / "bindings" / "rust_bridge.py").exists()
        if not rust_integrated:
            gaps.append({
                'type': 'rust_ffi_missing',
                'impact': 'high',
                'description': 'Rust performance claims unproven'
            })
        
        return {
            'gaps_found': len(gaps),
            'gaps': gaps
        }
    
    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns"""
        # Would integrate with logging/metrics
        return {
            'error_patterns': [],
            'recurring_issues': [],
            'fixes_needed': []
        }
    
    def _audit_documentation(self) -> Dict[str, Any]:
        """Audit documentation completeness"""
        docs_dir = self.base_dir / "docs"
        
        if not docs_dir.exists():
            return {'status': 'no_docs_dir'}
        
        md_files = list(docs_dir.rglob("*.md"))
        
        # Check for version references
        outdated = []
        for md_file in md_files:
            content = md_file.read_text()
            # Simple check - would be more sophisticated
            if '2.2.7' in content or '2.2.8' in content:
                outdated.append(str(md_file.relative_to(self.base_dir)))
        
        return {
            'total_docs': len(md_files),
            'potentially_outdated': len(outdated),
            'files': outdated[:10]
        }
    
    def _consolidate_memories(self) -> Dict[str, Any]:
        """Consolidate short-term memories"""
        short_term_dir = self.base_dir / "memory" / "short_term"
        
        if not short_term_dir.exists():
            return {'status': 'no_memories'}
        
        memories = list(short_term_dir.glob("*.md"))
        
        # Count old memories (>7 days)
        old_memories = []
        now = datetime.now()
        for mem in memories:
            age_days = (now.timestamp() - mem.stat().st_mtime) / 86400
            if age_days > 7:
                old_memories.append(mem.name)
        
        return {
            'total_short_term': len(memories),
            'old_memories': len(old_memories),
            'consolidation_candidates': old_memories[:20]
        }
    
    def _integrate_learning(self) -> Dict[str, Any]:
        """Integrate new learnings"""
        # Check emergence directory
        emergence_dir = self.base_dir / "whitemagic" / "emergence"
        
        if emergence_dir.exists():
            detector_file = emergence_dir / "detector.py"
            if detector_file.exists():
                return {
                    'emergence_system': 'active',
                    'status': 'integrated'
                }
        
        return {
            'emergence_system': 'unknown',
            'status': 'needs_verification'
        }
    
    def _save_analysis(self, results: Dict[str, Any]):
        """Save Yin analysis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"yin_analysis_{timestamp}.json"
        filepath = self.analysis_dir / filename
        
        filepath.write_text(json.dumps(results, indent=2))
        print(f"  📝 Analysis saved: {filepath.name}")

def run_yin_cycle():
    """Standalone Yin cycle execution"""
    yin = YinPhase()
    return yin.run_full_cycle()
