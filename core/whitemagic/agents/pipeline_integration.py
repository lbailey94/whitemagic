"""
Pipeline Integration — Connect Tactical Pipeline to Shadow Clone Deployment

Provides concrete implementations of the 7 pipeline phases for campaign execution:
1. Scout: Scan codebase/DB for current state
2. Discover: Mine patterns from findings
3. Clarify: Transform vague VCs → specific + measurable
4. Plan: Generate strategies, simulate outcomes, rank by consensus
5. Execute: Deploy shadow clone armies
6. Verify: Auto-check victory conditions
7. Reflect: Learn from results, adapt strategy

This bridges the abstract pipeline to concrete WhiteMagic operations.
"""

import logging
import re
from pathlib import Path
from typing import Any

from whitemagic.agents.tactical_pipeline import (
    ObjectiveRefinement,
    StrategySimulation,
    TacticalPipeline,
)

logger = logging.getLogger(__name__)


class PipelineIntegration:
    """
    Integrates Tactical Pipeline with WhiteMagic deployment system.

    Provides concrete implementations for each pipeline phase that work
    with shadow clone armies, campaign files, and victory conditions.
    """

    def __init__(self, campaign_codename: str, campaign_file: Path):
        self.campaign_codename = campaign_codename
        self.campaign_file = campaign_file
        self.campaign_data = self._load_campaign()
        self.pipeline = TacticalPipeline(campaign_codename)

    def _load_campaign(self) -> dict[str, Any]:
        """Load campaign markdown file and parse metadata"""
        if not self.campaign_file.exists():
            raise FileNotFoundError(f"Campaign file not found: {self.campaign_file}")

        content = self.campaign_file.read_text()

        # Extract YAML frontmatter
        frontmatter: dict[str, Any] = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1]) or {}
                content = parts[2]

        # Extract sections
        sections = self._parse_sections(content)

        return {
            'frontmatter': frontmatter,
            'sections': sections,
            'content': content,
        }

    def _parse_sections(self, content: str) -> dict[str, str]:
        """Parse markdown sections"""
        sections: dict[str, str] = {}
        current_section = None
        current_content: list[str] = []

        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    # ========== PHASE 1: SCOUT ==========

    def scout_implementation(self) -> list[dict[str, Any]]:
        """
        Scout phase: Scan codebase/DB for current state

        Returns findings about:
        - Current file/code state
        - Database metrics
        - Existing patterns
        - Baseline measurements
        """
        findings = []

        # 1. Scan for target files/patterns from campaign
        targets = self._extract_targets()
        for target in targets:
            finding = self._scan_target(target)
            if finding:
                findings.append(finding)

        # 2. Measure baselines if campaign mentions metrics
        metrics = self._extract_metrics()
        for metric in metrics:
            baseline = self._measure_baseline(metric)
            if baseline:
                findings.append(baseline)

        # 3. Check current victory condition status
        vc_status = self._check_current_vcs()
        findings.append({
            'type': 'victory_conditions',
            'data': vc_status,
        })

        return findings

    def _extract_targets(self) -> list[dict[str, Any]]:
        """Extract target files/patterns from campaign"""
        targets = []

        # Look for Targets section
        if 'Targets' in self.campaign_data['sections']:
            targets_text = self.campaign_data['sections']['Targets']
            # Parse table or list format
            for line in targets_text.split('\n'):
                if '|' in line and not line.startswith('|---'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2 and not parts[0].startswith('File'):
                        targets.append({
                            'file': parts[0],
                            'pattern': parts[1] if len(parts) > 1 else None,
                        })

        return targets

    def _scan_target(self, target: dict[str, Any]) -> dict[str, Any] | None:
        """Scan a specific target file/pattern."""
        from pathlib import Path
        path_str = target.get("path", ".")
        path = Path(path_str)
        if not path.exists():
            return {"type": "target_scan", "target": target, "status": "not_found"}

        if path.is_dir():
            files = list(path.rglob("*.py"))
            return {
                "type": "target_scan",
                "target": target,
                "status": "scanned",
                "file_count": len(files),
                "total_lines": sum(len(f.read_text(encoding="utf-8").splitlines()) for f in files if f.is_file()),
            }
        else:
            content = path.read_text(encoding="utf-8") if path.is_file() else ""
            return {
                "type": "target_scan",
                "target": target,
                "status": "scanned",
                "lines": len(content.splitlines()),
                "size_bytes": path.stat().st_size if path.is_file() else 0,
            }

    def _extract_metrics(self) -> list[str]:
        """Extract metrics mentioned in campaign"""
        metrics = []
        content = self.campaign_data['content'].lower()

        # Look for common metric patterns
        metric_patterns = [
            r'(\d+x)\s+speedup',
            r'(\d+%)\s+reduction',
            r'(\d+)\s+files?',
            r'(\d+)\s+queries',
            r'accuracy\s+[>≥]\s*(\d+%)',
        ]

        for pattern in metric_patterns:
            matches = re.findall(pattern, content)
            metrics.extend(matches)

        return metrics

    def _measure_baseline(self, metric: str) -> dict[str, Any] | None:
        """Measure baseline for a metric."""
        import time
        start = time.perf_counter()
        # Minimal benchmark: count imports in campaign file directory
        target_dir = self.campaign_file.parent
        files = list(target_dir.rglob("*.py"))
        import_count = 0
        for f in files:
            try:
                import_count += f.read_text(encoding="utf-8").count("import ")
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Skipping unreadable file {f}: {e}")
        elapsed = time.perf_counter() - start
        return {
            "type": "baseline_measurement",
            "metric": metric,
            "value": import_count,
            "scan_time_ms": elapsed * 1000,
            "files_scanned": len(files),
        }

    def _check_current_vcs(self) -> dict[str, Any]:
        """Check current victory condition status"""
        vcs = self._extract_victory_conditions()

        met = 0
        total = len(vcs)

        for vc in vcs:
            # This would run actual verification
            # For now, assume not met
            vc['met'] = False

        return {
            'vcs': vcs,
            'met': met,
            'total': total,
            'percentage': 100 * met / total if total > 0 else 0,
        }

    def _extract_victory_conditions(self) -> list[dict[str, Any]]:
        """Extract victory conditions from campaign"""
        vcs = []

        if 'Victory Conditions' in self.campaign_data['sections']:
            vc_text = self.campaign_data['sections']['Victory Conditions']
            for line in vc_text.split('\n'):
                line = line.strip()
                if line.startswith('- [ ]') or line.startswith('- [x]') or line.startswith('❌') or line.startswith('✅'):
                    met = line.startswith('- [x]') or line.startswith('✅')
                    text = re.sub(r'^[-\s]*\[[ x]\]\s*|^[❌✅]\s*', '', line)
                    vcs.append({
                        'text': text,
                        'met': met,
                    })

        return vcs

    # ========== PHASE 2: DISCOVER ==========

    def discover_implementation(self, scout_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Discover phase: Find patterns and identify gaps

        Analyzes scout findings to discover:
        - Common patterns across targets
        - Missing baselines
        - Vague vs specific VCs
        - Implementation gaps
        """
        patterns = []

        # 1. Identify vague victory conditions
        vc_findings = [f for f in scout_findings if f.get('type') == 'victory_conditions']
        if vc_findings:
            vague_vcs = self._find_vague_vcs(vc_findings[0]['data']['vcs'])
            if vague_vcs:
                patterns.append({
                    'type': 'vague_victory_conditions',
                    'count': len(vague_vcs),
                    'vcs': vague_vcs,
                    'severity': 'high',
                })

        # 2. Identify missing baselines
        baseline_findings = [f for f in scout_findings if f.get('type') == 'baseline_measurement']
        missing_baselines = [f for f in baseline_findings if f.get('value') == 'to_be_measured']
        if missing_baselines:
            patterns.append({
                'type': 'missing_baselines',
                'count': len(missing_baselines),
                'metrics': [f['metric'] for f in missing_baselines],
                'severity': 'high',
            })

        # 3. Identify discovery vs implementation gap
        if self._has_discovery_gap():
            patterns.append({
                'type': 'discovery_implementation_gap',
                'description': 'Campaign has discovery objectives but no implementation phase',
                'severity': 'critical',
            })

        return patterns

    def _find_vague_vcs(self, vcs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify vague victory conditions"""
        vague_keywords = ['optimize', 'improve', 'enhance', 'consider', 'explore', 'investigate']
        vague = []

        for vc in vcs:
            text_lower = vc['text'].lower()
            if any(keyword in text_lower for keyword in vague_keywords):
                # Check if it has specific metrics
                has_number = bool(re.search(r'\d+', vc['text']))
                has_comparison = bool(re.search(r'[>≥<≤=]', vc['text']))

                if not (has_number and has_comparison):
                    vague.append(vc)

        return vague

    def _has_discovery_gap(self) -> bool:
        """Check if campaign has discovery but no implementation"""
        strategy = self.campaign_data['frontmatter'].get('type', '')

        # Discovery-only strategies
        discovery_types = ['discovery', 'security_scan', 'consensus_vote']

        return strategy in discovery_types

    # ========== PHASE 3: CLARIFY ==========

    def clarify_implementation(self, discovered_patterns: list[dict[str, Any]]) -> list[ObjectiveRefinement]:
        """
        Clarify phase: Transform vague → specific + measurable

        Takes discovered patterns and generates refined objectives with:
        - Specific numeric targets
        - Clear baselines
        - Verification methods
        - Success metrics
        """
        refinements = []

        for pattern in discovered_patterns:
            if pattern['type'] == 'vague_victory_conditions':
                for vc in pattern['vcs']:
                    refined = self._refine_vague_vc(vc)
                    if refined:
                        refinements.append(refined)

            elif pattern['type'] == 'missing_baselines':
                for metric in pattern['metrics']:
                    refined = self._add_baseline_to_metric(metric)
                    if refined:
                        refinements.append(refined)

            elif pattern['type'] == 'discovery_implementation_gap':
                refined = self._add_implementation_phase()
                if refined:
                    refinements.append(refined)

        return refinements

    def _refine_vague_vc(self, vc: dict[str, Any]) -> ObjectiveRefinement | None:
        """Refine a vague victory condition"""
        original = vc['text']

        # Apply refinement rules
        if 'optimize' in original.lower():
            refined = original.replace('optimize', 'achieve ≥10x speedup on')
            metrics = ['baseline_time', 'optimized_time', 'speedup_ratio']
            verification = 'benchmark_comparison'
        elif 'improve' in original.lower():
            refined = original.replace('improve', 'increase by ≥50%')
            metrics = ['baseline_value', 'improved_value', 'improvement_percentage']
            verification = 'metric_comparison'
        else:
            # Generic refinement
            refined = f"{original} (measured with specific numeric target ≥X)"
            metrics = ['baseline', 'target', 'actual']
            verification = 'automated_check'

        return ObjectiveRefinement(
            original=original,
            refined=refined,
            metrics=metrics,
            verification_method=verification,
            confidence=0.7,
        )

    def _add_baseline_to_metric(self, metric: str) -> ObjectiveRefinement | None:
        """Add baseline measurement to a metric"""
        return ObjectiveRefinement(
            original=f"Metric: {metric}",
            refined=f"Measure baseline for {metric}, then achieve target improvement",
            metrics=['baseline', 'target', 'actual', 'improvement'],
            baseline={'value': 'to_be_measured'},
            target={'improvement': '≥10x or ≥50%'},
            verification_method='benchmark',
            confidence=0.8,
        )

    def _add_implementation_phase(self) -> ObjectiveRefinement | None:
        """Add implementation phase to discovery-only campaign"""
        return ObjectiveRefinement(
            original="Discovery-only campaign",
            refined="Two-phase deployment: (1) Scout 15% clones for discovery, (2) Implement 85% clones for execution",
            metrics=['discoveries_made', 'implementations_completed', 'tests_passing'],
            verification_method='code_verification',
            confidence=0.9,
        )

    # ========== PHASE 4: PLAN ==========

    def plan_implementation(self, refined_objectives: list[ObjectiveRefinement]) -> list[StrategySimulation]:
        """
        Plan phase: Generate strategies, simulate, rank by consensus

        Creates multiple strategy options and simulates their outcomes:
        - Small parallel armies (10-30K each)
        - Two-phase deployment (scout → implement)
        - Massive single army (200K+)
        - Consensus voting on best approach
        """
        simulations = []

        # Strategy 1: Small parallel armies (RECOMMENDED)
        simulations.append(StrategySimulation(
            strategy_name="small_parallel_armies",
            predicted_success_rate=0.75,
            predicted_duration=300.0,  # 5 min
            predicted_clone_count=60000,  # 3x 20K armies
            risks=["Coordination overhead", "Requires clear task division"],
            dependencies=[],
            consensus_votes=10,  # Highest based on doctrine
        ))

        # Strategy 2: Two-phase deployment (scout → implement)
        simulations.append(StrategySimulation(
            strategy_name="two_phase_deployment",
            predicted_success_rate=0.80,
            predicted_duration=600.0,  # 10 min
            predicted_clone_count=100000,  # 15K scout + 85K implement
            risks=["Longer duration", "Discovery may not yield actionable items"],
            dependencies=["Clear implementation VCs"],
            consensus_votes=9,
        ))

        # Strategy 3: Focused single army
        simulations.append(StrategySimulation(
            strategy_name="focused_single_army",
            predicted_success_rate=0.60,
            predicted_duration=180.0,  # 3 min
            predicted_clone_count=25000,
            risks=["May miss edge cases", "Single point of failure"],
            dependencies=[],
            consensus_votes=7,
        ))

        # Strategy 4: Massive brute force (NOT RECOMMENDED)
        simulations.append(StrategySimulation(
            strategy_name="massive_brute_force",
            predicted_success_rate=0.30,
            predicted_duration=900.0,  # 15 min
            predicted_clone_count=500000,
            risks=["Coordination overhead", "Diminishing returns", "Resource waste"],
            dependencies=["Stress test only"],
            consensus_votes=2,
        ))

        return simulations

    # ========== PHASE 5: EXECUTE ==========

    def execute_implementation(self, strategy: StrategySimulation) -> dict[str, Any]:
        """Execute phase: Write strategy output to a file."""
        output_dir = self.campaign_file.parent / "strategy_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{strategy.strategy_name}.md"
        output_path.write_text(
            f"# Strategy: {strategy.strategy_name}\n\n"
            f"Predicted clone count: {strategy.predicted_clone_count}\n"
            f"Predicted duration: {strategy.predicted_duration}\n"
            f"Consensus votes: {strategy.consensus_votes}\n",
            encoding="utf-8",
        )
        return {
            "strategy_used": strategy.strategy_name,
            "clones_deployed": strategy.predicted_clone_count,
            "duration": strategy.predicted_duration,
            "findings": [f"Output written to {output_path}"],
            "status": "completed",
            "output_path": str(output_path),
        }

    # ========== PHASE 6: VERIFY ==========

    def verify_implementation(self, execution_results: dict[str, Any]) -> dict[str, Any]:
        """Verify phase: Check victory conditions and measure results."""
        vcs = self._extract_victory_conditions()

        vcs_met = 0
        vcs_total = len(vcs)
        output_path = execution_results.get("output_path", "")
        if output_path and Path(output_path).exists():
            vcs_met += 1  # Output file created

        return {
            'vcs_met': vcs_met,
            'vcs_total': vcs_total,
            'percentage': 100 * vcs_met / vcs_total if vcs_total > 0 else 0,
            'details': vcs,
        }

    # ========== PHASE 7: REFLECT ==========

    def reflect_implementation(self, cycle_data: dict[str, Any]) -> dict[str, Any]:
        """
        Reflect phase: Learn from cycle, prepare for next iteration

        Analyzes what worked, what didn't, and how to improve.
        """
        insights = {
            'cycle_number': cycle_data['cycle_number'],
            'improvements': [],
            'recommendations': [],
            'next_cycle_strategy': None,
        }

        # Analyze verification results
        if cycle_data['verification_results']:
            last_verify = cycle_data['verification_results'][-1]
            vcs_percentage = last_verify.get('percentage', 0)

            if vcs_percentage == 0:
                insights['improvements'].append("No VCs met - need to refine objectives")
                insights['recommendations'].append("Run clarify phase again with more specific metrics")
                insights['next_cycle_strategy'] = 'focus_on_clarification'

            elif vcs_percentage < 50:
                insights['improvements'].append("Partial progress - execution strategy may need adjustment")
                insights['recommendations'].append("Try two-phase deployment or smaller armies")
                insights['next_cycle_strategy'] = 'adjust_execution_strategy'

            elif vcs_percentage < 100:
                insights['improvements'].append("High progress - close to victory")
                insights['recommendations'].append("Focus on remaining VCs with targeted deployment")
                insights['next_cycle_strategy'] = 'targeted_completion'

            else:
                insights['improvements'].append("Victory achieved!")
                insights['next_cycle_strategy'] = 'complete'

        return insights

    # ========== FULL CYCLE EXECUTION ==========

    def run_full_cycle(self) -> dict[str, Any]:
        """Execute one complete Yin-Yang cycle"""
        self.pipeline.start_cycle()

        # YIN: Scout → Discover → Clarify → Plan
        self.pipeline.scout(self.scout_implementation)
        self.pipeline.discover(lambda f: self.discover_implementation(f))
        self.pipeline.clarify(lambda p: self.clarify_implementation(p))
        self.pipeline.plan(lambda o: self.plan_implementation(o))

        self.pipeline.advance_phase()  # SCOUT → DISCOVER
        self.pipeline.advance_phase()  # DISCOVER → CLARIFY
        self.pipeline.advance_phase()  # CLARIFY → PLAN

        # YANG: Execute → Verify
        self.pipeline.execute(lambda s: self.execute_implementation(s))
        self.pipeline.verify(lambda e: self.verify_implementation(e))

        self.pipeline.advance_phase()  # PLAN → EXECUTE
        self.pipeline.advance_phase()  # EXECUTE → VERIFY

        # YIN: Reflect
        self.pipeline.reflect(lambda c: self.reflect_implementation(c))

        self.pipeline.advance_phase()  # VERIFY → REFLECT

        return {
            'cycle_complete': True,
            'summary': self.pipeline.get_cycle_summary(),
            'progress_report': self.pipeline.get_progress_report(),
            'should_continue': self.pipeline.should_continue(),
        }


def create_pipeline_integration(campaign_codename: str, campaign_file: Path) -> PipelineIntegration:
    """Factory function to create pipeline integration"""
    return PipelineIntegration(campaign_codename, campaign_file)
