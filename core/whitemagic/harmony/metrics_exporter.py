"""Prometheus-compatible metrics exporter for WhiteMagic.

Exports system metrics in Prometheus text exposition format, including:
- Cognitive metrics (tool dispatch counts, error rates, harmony scores)
- Physical metrics from laptop-optimizer (CPU temp, battery, memory, etc.)
- STRATA codebase quality metrics

Usage:
    from whitemagic.harmony.metrics_exporter import get_metrics_exporter
    exporter = get_metrics_exporter()
    prometheus_text = exporter.export()
"""
# ruff: noqa: BLE001

import logging

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Exports WhiteMagic metrics in Prometheus text exposition format.

    Integrates physical metrics from laptop-optimizer when available.
    """

    def export(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines: list[str] = []
        lines.extend(self._export_cognitive_metrics())
        lines.extend(self._export_physical_metrics())
        lines.extend(self._export_strata_metrics())
        return "\n".join(lines) + "\n"

    def _export_cognitive_metrics(self) -> list[str]:
        """Export cognitive system metrics."""
        lines: list[str] = []

        # Tool dispatch metrics
        try:
            from whitemagic.tools.unified_api import get_dispatch_stats
            stats = get_dispatch_stats()
            lines.append("# HELP whitemagic_tool_dispatches_total Total tool dispatches")
            lines.append("# TYPE whitemagic_tool_dispatches_total counter")
            lines.append(f'whitemagic_tool_dispatches_total {stats.get("total_dispatches", 0)}')

            lines.append("# HELP whitemagic_tool_errors_total Total tool errors")
            lines.append("# TYPE whitemagic_tool_errors_total counter")
            lines.append(f'whitemagic_tool_errors_total {stats.get("total_errors", 0)}')

            lines.append("# HELP whitemagic_active_tools Number of active tools")
            lines.append("# TYPE whitemagic_active_tools gauge")
            lines.append(f'whitemagic_active_tools {stats.get("active_tools", 0)}')
        except Exception:
            pass

        # Harmony vector metrics
        try:
            from whitemagic.harmony.vector import get_harmony_vector
            snap = get_harmony_vector().snapshot()
            lines.append("# HELP whitemagic_harmony_score Composite harmony score")
            lines.append("# TYPE whitemagic_harmony_score gauge")
            lines.append(f"whitemagic_harmony_score {snap.harmony_score:.4f}")

            lines.append("# HELP whitemagic_error_rate Error rate dimension")
            lines.append("# TYPE whitemagic_error_rate gauge")
            lines.append(f"whitemagic_error_rate {snap.error_rate:.4f}")

            lines.append("# HELP whitemagic_energy Energy dimension")
            lines.append("# TYPE whitemagic_energy gauge")
            lines.append(f"whitemagic_energy {snap.energy:.4f}")

            lines.append("# HELP whitemagic_dharma Dharma dimension")
            lines.append("# TYPE whitemagic_dharma gauge")
            lines.append(f"whitemagic_dharma {snap.dharma:.4f}")

            lines.append("# HELP whitemagic_karma_debt Karma debt dimension")
            lines.append("# TYPE whitemagic_karma_debt gauge")
            lines.append(f"whitemagic_karma_debt {snap.karma_debt:.4f}")

            lines.append("# HELP whitemagic_latency Latency dimension")
            lines.append("# TYPE whitemagic_latency gauge")
            lines.append(f"whitemagic_latency {snap.latency:.4f}")
        except Exception:
            pass

        # Homeostatic loop metrics
        try:
            from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop
            loop = get_homeostatic_loop()
            stats = loop.get_stats()
            lines.append("# HELP whitemagic_homeostatic_checks_total Total homeostatic checks")
            lines.append("# TYPE whitemagic_homeostatic_checks_total counter")
            lines.append(f'whitemagic_homeostatic_checks_total {stats.get("total_checks", 0)}')

            lines.append("# HELP whitemagic_homeostatic_actions_total Total corrective actions")
            lines.append("# TYPE whitemagic_homeostatic_actions_total counter")
            lines.append(f'whitemagic_homeostatic_actions_total {stats.get("total_actions", 0)}')
        except Exception:
            pass

        # Memory metrics
        try:
            import sqlite3

            from whitemagic.config.paths import DB_PATH
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memories")
            mem_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT tag) FROM tags")
            tag_count = cur.fetchone()[0]
            conn.close()

            lines.append("# HELP whitemagic_memories_total Total memories in database")
            lines.append("# TYPE whitemagic_memories_total gauge")
            lines.append(f"whitemagic_memories_total {mem_count}")

            lines.append("# HELP whitemagic_tags_total Total unique tags")
            lines.append("# TYPE whitemagic_tags_total gauge")
            lines.append(f"whitemagic_tags_total {tag_count}")
        except Exception:
            pass

        return lines

    def _export_physical_metrics(self) -> list[str]:
        """Export physical system metrics from laptop-optimizer."""
        lines: list[str] = []

        try:
            from whitemagic.harmony.physical_metrics import get_physical_metrics_source
            source = get_physical_metrics_source()
            metrics = source.get_metrics()
            if not metrics.is_available:
                return lines

            if metrics.cpu_temp is not None:
                lines.append("# HELP whitemagic_cpu_temp_celsius CPU package temperature")
                lines.append("# TYPE whitemagic_cpu_temp_celsius gauge")
                lines.append(f"whitemagic_cpu_temp_celsius {metrics.cpu_temp:.1f}")

            if metrics.cpu_usage is not None:
                lines.append("# HELP whitemagic_cpu_usage_percent CPU usage percentage")
                lines.append("# TYPE whitemagic_cpu_usage_percent gauge")
                lines.append(f"whitemagic_cpu_usage_percent {metrics.cpu_usage:.1f}")

            if metrics.battery_percent is not None:
                lines.append("# HELP whitemagic_battery_percent Battery charge percentage")
                lines.append("# TYPE whitemagic_battery_percent gauge")
                lines.append(f"whitemagic_battery_percent {metrics.battery_percent:.1f}")

            if metrics.memory_percent is not None:
                lines.append("# HELP whitemagic_memory_percent Memory usage percentage")
                lines.append("# TYPE whitemagic_memory_percent gauge")
                lines.append(f"whitemagic_memory_percent {metrics.memory_percent:.1f}")

            if metrics.swap_percent is not None:
                lines.append("# HELP whitemagic_swap_percent Swap usage percentage")
                lines.append("# TYPE whitemagic_swap_percent gauge")
                lines.append(f"whitemagic_swap_percent {metrics.swap_percent:.1f}")

            if metrics.disk_usage is not None:
                lines.append("# HELP whitemagic_disk_usage_percent Disk usage percentage")
                lines.append("# TYPE whitemagic_disk_usage_percent gauge")
                lines.append(f"whitemagic_disk_usage_percent {metrics.disk_usage:.1f}")

            if metrics.power_draw is not None:
                lines.append("# HELP whitemagic_power_draw_microwatts Power draw in microwatts")
                lines.append("# TYPE whitemagic_power_draw_microwatts gauge")
                lines.append(f"whitemagic_power_draw_microwatts {metrics.power_draw:.0f}")

            if metrics.fan_rpm is not None:
                lines.append("# HELP whitemagic_fan_rpm Fan speed in RPM")
                lines.append("# TYPE whitemagic_fan_rpm gauge")
                lines.append(f"whitemagic_fan_rpm {metrics.fan_rpm:.0f}")

            if metrics.thermal_throttling > 0:
                lines.append("# HELP whitemagic_thermal_throttling_cores Cores throttling")
                lines.append("# TYPE whitemagic_thermal_throttling_cores gauge")
                lines.append(f"whitemagic_thermal_throttling_cores {metrics.thermal_throttling}")

            if metrics.health_score is not None:
                lines.append("# HELP whitemagic_physical_health_score Laptop-optimizer health score")
                lines.append("# TYPE whitemagic_physical_health_score gauge")
                lines.append(f"whitemagic_physical_health_score {metrics.health_score:.1f}")

            # Thermal forecast
            forecast = source.get_thermal_forecast()
            if forecast:
                lines.append("# HELP whitemagic_thermal_forecast_5min Predicted CPU temp in 5 minutes")
                lines.append("# TYPE whitemagic_thermal_forecast_5min gauge")
                lines.append(f"whitemagic_thermal_forecast_5min {forecast.predicted_5min:.1f}")

                lines.append("# HELP whitemagic_thermal_forecast_15min Predicted CPU temp in 15 minutes")
                lines.append("# TYPE whitemagic_thermal_forecast_15min gauge")
                lines.append(f"whitemagic_thermal_forecast_15min {forecast.predicted_15min:.1f}")

        except Exception:
            pass

        return lines

    def _export_strata_metrics(self) -> list[str]:
        """Export STRATA codebase quality metrics."""
        lines: list[str] = []

        try:
            from pathlib import Path

            from whitemagic.tools.strata import Strata

            core_path = str(Path(__file__).parent.parent.parent.parent.parent)
            if not Path(core_path, "AGENTS.md").exists():
                return lines

            strata = Strata(core_path)
            findings = strata.analyze(incremental=True)

            severity_counts = {"error": 0, "warning": 0, "info": 0}
            category_counts: dict[str, int] = {}
            for f in findings:
                severity_counts[f.severity.value] += 1
                category_counts[f.category] = category_counts.get(f.category, 0) + 1

            lines.append("# HELP whitemagic_strata_errors_total STRATA ERROR findings")
            lines.append("# TYPE whitemagic_strata_errors_total gauge")
            lines.append(f'whitemagic_strata_errors_total {severity_counts["error"]}')

            lines.append("# HELP whitemagic_strata_warnings_total STRATA WARNING findings")
            lines.append("# TYPE whitemagic_strata_warnings_total gauge")
            lines.append(f'whitemagic_strata_warnings_total {severity_counts["warning"]}')

            lines.append("# HELP whitemagic_strata_info_total STRATA INFO findings")
            lines.append("# TYPE whitemagic_strata_info_total gauge")
            lines.append(f'whitemagic_strata_info_total {severity_counts["info"]}')

            for category, count in sorted(category_counts.items()):
                safe_cat = category.replace("-", "_").replace(".", "_")
                lines.append(
                    f'whitemagic_strata_findings{{category="{safe_cat}"}} {count}'
                )

        except Exception:
            pass

        return lines


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_exporter: MetricsExporter | None = None


def get_metrics_exporter() -> MetricsExporter:
    """Get the singleton MetricsExporter."""
    global _exporter
    if _exporter is None:
        _exporter = MetricsExporter()
    return _exporter
